import requests
import feedparser
import re
from datetime import datetime
import os
import argparse
import time
import logging
import sqlite3
import unicodedata
from urllib.parse import urlparse, unquote
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TALB, TPE1, TIT2, TDRC, COMM, TPE2, TCON

"""
RSS Downloader Script

Description: This script is designed to download audio files and accompanying text information from a specified RSS 
feed. It allows for saving the downloaded files in a designated directory and optionally saves additional episode 
details in text format.

Usage: To use the script, provide the RSS feed URL and the directory where the files will be saved. The --save_text 
flag can be used to save additional episode details in a text file.

Example:
python ripper.py <RSS_FEED_URL> <SAVE_DIRECTORY> [--save_text]

Note:

I haven't tested extensively, in my tests I included the authentication token in the URL and it worked fine.

Features:
- Downloads audio files from the provided RSS feed.
- Optionally saves additional episode details in a separate text file.
- Sanitizes titles to create filesystem-friendly filenames.
- Allows for command-line arguments to specify RSS feed and save directory.

Requirements:
- Python 3.x
- Install required packages using pip: pip install -r requirements.txt

Please ensure proper use in accordance with the terms of service of the RSS feed provider. This script is intended 
for personal use and should be used responsibly.

Author: John Sosoka
"""

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_database():
    """Initializes the SQLite database in the script's directory."""
    script_dir = os.path.dirname(os.path.realpath(__file__))
    db_path = os.path.join(script_dir, 'downloads.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Simple migration: check if episodes table has feed_id. If not, archive it.
    try:
        cursor.execute("PRAGMA table_info(episodes)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'feed_id' not in columns:
            logging.warning("Old database schema detected. Archiving old 'episodes' table and creating new schema. Download history will be reset.")
            cursor.execute("ALTER TABLE episodes RENAME TO episodes_old_pre_multi_feed")
    except sqlite3.OperationalError:
        # This happens if the episodes table doesn't exist at all, which is fine.
        pass

    # Create tables with the new schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feeds (
            feed_id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_url TEXT UNIQUE NOT NULL,
            feed_title TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS episodes (
            episode_id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_id INTEGER NOT NULL,
            guid TEXT NOT NULL,
            title TEXT,
            published TEXT,
            filepath TEXT,
            downloaded_at TEXT,
            FOREIGN KEY (feed_id) REFERENCES feeds (feed_id),
            UNIQUE (feed_id, guid)
        )
    ''')
    conn.commit()
    logging.info(f"Database setup complete at {db_path}")
    return conn

def get_or_create_feed(conn, feed_url, feed_title):
    """Gets the feed_id for a given feed_url, creating it if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute("SELECT feed_id FROM feeds WHERE feed_url = ?", (feed_url,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        cursor.execute("INSERT INTO feeds (feed_url, feed_title) VALUES (?, ?)", (feed_url, feed_title))
        conn.commit()
        logging.info(f"Added new feed to database: {feed_title}")
        return cursor.lastrowid


def sanitize_title(title, date_str=None):
    """
    Convert a podcast episode title to a filesystem-friendly filename,
    prepending the date in the format (YYYY-MM-DD) if provided.
    """
    # Normalize unicode characters to their ASCII equivalent
    try:
        normalized_title = unicodedata.normalize('NFKD', title)
        ascii_title = normalized_title.encode('ascii', 'ignore').decode('ascii')
    except Exception as e:
        logging.warning(f"Could not normalize title '{title}'. Using it as is. Error: {e}")
        ascii_title = title

    # Replace dashes and spaces
    sanitized_title = ascii_title.replace(' ', '_')
    
    # Remove any character that is not a letter, a number, a dot, an underscore or a dash.
    sanitized_title = re.sub(r'[^a-zA-Z0-9._-]', '', sanitized_title)

    # Collapse multiple underscores or dashes
    sanitized_title = re.sub(r'__+', '_', sanitized_title)
    sanitized_title = re.sub(r'--+', '-', sanitized_title)
    
    # Remove leading/trailing underscores or dashes
    sanitized_title = sanitized_title.strip('_-')

    # Convert to lowercase
    sanitized_title = sanitized_title.lower()

    # Prepend date in the specified format if provided
    if date_str:
        date = None
        # List of common date formats to try for RSS feeds
        formats_to_try = [
            '%a, %d %b %Y %H:%M:%S %Z',  # With timezone name e.g. GMT
            '%a, %d %b %Y %H:%M:%S %z',  # With timezone offset e.g. +0000
            '%a, %d %b %Y %H:%M:%S',    # Without timezone
        ]

        for format_str in formats_to_try:
            try:
                date = datetime.strptime(date_str, format_str)
                break  # Successfully parsed
            except ValueError:
                continue  # Try the next format

        if date:
            date_formatted = date.strftime('%Y-%m-%d')
            sanitized_title = f'{date_formatted}_{sanitized_title}'
        else:
            logging.warning(f"Could not parse date: '{date_str}'. Filename will not have a date prefix.")

    return sanitized_title

def download_file(url, filename, retries=3):
    """Download a file from a given URL with retry logic."""
    attempt = 0
    while attempt < retries:
        try:
            response = requests.get(url)
            response.raise_for_status()
            with open(filename, 'wb') as file:
                file.write(response.content)
            if attempt > 0:
                logging.info(f"Download succeeded after {attempt} retry(ies): {filename}")
            else:
                logging.info(f"Downloaded: {filename}")
            return True
        except requests.RequestException as e:
            attempt += 1
            logging.warning(f"Error downloading file (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                sleep_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
                logging.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                logging.error(f"Failed to download {url} after {retries} attempts.")
    return False

def fetch_rss_feed(url):
    """Fetch the content of the RSS feed."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        logging.error(f"Error fetching the RSS feed: {e}")
        logging.error("Please check the URL and authentication token (if applicable)")
        logging.error("Exiting...")
        exit(1)

def save_text_file(entry, filename):
    """Save podcast details in a text file."""
    with open(f"{filename}.txt", 'w') as file:
        file.write(f"Title: {entry.get('title', 'N/A')}\n")
        file.write(f"Subtitle: {entry.get('subtitle', 'N/A')}\n")
        file.write(f"Published Date: {entry.get('published', 'N/A')}\n")
        file.write(f"Content: {entry.get('summary', 'N/A')}\n")

def set_mp3_tags(filename, entry, feed):
    """Set MP3 tags using metadata from the RSS feed."""
    try:
        audio = MP3(filename, ID3=ID3)
    except Exception as e:
        logging.error(f"Could not open file for tagging: {filename} - {e}")
        return

    # Add ID3 tag if it doesn't exist
    if audio.tags is None:
        audio.add_tags()

    # Album (Podcast Title)
    if 'title' in feed.feed:
        audio.tags.add(TALB(encoding=3, text=feed.feed.title))

    # Artist (Podcast Author)
    artist = entry.get('author') or feed.feed.get('author')
    if artist:
        audio.tags.add(TPE1(encoding=3, text=artist))
        audio.tags.add(TPE2(encoding=3, text=artist))

    # Title (Episode Title)
    if 'title' in entry:
        audio.tags.add(TIT2(encoding=3, text=entry.title))
    
    # Date (Published Date)
    if entry.get('published_parsed'):
        pub_date = datetime(*entry.published_parsed[:6])
        audio.tags.add(TDRC(encoding=3, text=pub_date.strftime('%Y-%m-%dT%H:%M:%S')))
    
    # Comment (Summary)
    summary = entry.get('summary')
    if summary:
        audio.tags.add(COMM(encoding=3, lang='eng', text=summary))
        
    # Genre from RSS category
    if hasattr(feed.feed, 'tags') and feed.feed.tags:
        genre = feed.feed.tags[0].term
        audio.tags.add(TCON(encoding=3, text=genre))

    audio.save()
    logging.info(f"Successfully set MP3 tags for: {filename}")


def parse_and_download(content, save_dir, save_text, num_episodes=None, conn=None, feed_id=None, feed=None):
    """Parse the RSS feed and download files."""
    if not conn or not feed_id or not feed:
        logging.error("Database connection, feed_id, or feed object not provided.")
        return

    cursor = conn.cursor()

    all_episodes = [
        (entry, link)
        for entry in feed.entries
        for link in entry.get('links', [])
        if link.type == 'audio/mpeg'
    ]

    # If --num-episodes is used, only consider the latest N episodes from the feed
    episodes_to_consider = all_episodes
    if num_episodes is not None:
        logging.info(f"--num-episodes set to {num_episodes}. Considering only the latest {num_episodes} episodes from the feed.")
        episodes_to_consider = all_episodes[:num_episodes]

    # Filter out episodes that have already been downloaded from the considered list
    episodes_to_download = []
    for entry, link in episodes_to_consider:
        guid = entry.get('id', link.href)
        cursor.execute("SELECT guid FROM episodes WHERE feed_id = ? AND guid = ?", (feed_id, guid))
        if not cursor.fetchone():
            episodes_to_download.append((entry, link))

    total_to_download = len(episodes_to_download)
    logging.info(f"Found {len(all_episodes)} total episodes. Considering {len(episodes_to_consider)}. Found {total_to_download} new episodes to download.")

    successful_downloads = 0
    for i, (entry, link) in enumerate(episodes_to_download):
        date_str = entry.get('published', None)
        title = sanitize_title(entry.title, date_str)

        # Parse URL for file extension
        parsed_url = urlparse(unquote(link.href))
        _, file_extension = os.path.splitext(parsed_url.path)
        if not file_extension and link.type == 'audio/mpeg':
            file_extension = '.mp3'
            
        filename = os.path.join(save_dir, title + file_extension)

        logging.info(f"Downloading audio file {i + 1} of {total_to_download}: {title}")
        # Attempt to download the file
        if download_file(link.href, filename):
            guid = entry.get('id', link.href)
            published_iso = ''
            if entry.get('published_parsed'):
                published_iso = datetime(*entry.published_parsed[:6]).strftime('%Y-%m-%dT%H:%M:%S')

            try:
                cursor.execute(
                    "INSERT INTO episodes (feed_id, guid, title, published, filepath, downloaded_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (feed_id, guid, entry.title, published_iso, filename, datetime.now().isoformat())
                )
                conn.commit()
                successful_downloads += 1
            except sqlite3.IntegrityError:
                logging.warning(f"Episode with GUID {guid} already in database for this feed. Skipping DB entry.")
                continue

            # Set MP3 tags
            if filename.lower().endswith('.mp3'):
                set_mp3_tags(filename, entry, feed)

            if save_text:
                save_text_file(entry, filename)
        
        if i < total_to_download - 1:
            logging.info("Sleeping for 1 second...")
            time.sleep(1)

    logging.info("Completed! Successfully downloaded {} / {} audio files".format(successful_downloads, total_to_download))

def main():
    parser = argparse.ArgumentParser(description='RSS Podcast Downloader')
    parser.add_argument('rss_url', help='RSS feed URL (Include authentication token if applicable)')
    parser.add_argument('save_dir', help='Directory to save downloaded files')
    parser.add_argument('--save_text', action='store_true', help='Flag to save text files with extra episode data')
    parser.add_argument('--num-episodes', type=int, default=None, help='Number of additional episodes to download')
    args = parser.parse_args()

    # Create save_dir if it doesn't exist
    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)

    conn = None
    try:
        content = fetch_rss_feed(args.rss_url)
        if content:
            feed = feedparser.parse(content)
            conn = setup_database()
            feed_id = get_or_create_feed(conn, args.rss_url, feed.feed.get('title', 'N/A'))
            parse_and_download(content, args.save_dir, args.save_text, args.num_episodes, conn, feed_id, feed)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")

if __name__ == "__main__":
    main()
