import requests
import feedparser
import re
from datetime import datetime
import os
import argparse
import time
import logging
from urllib.parse import urlparse, unquote

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

def sanitize_title(title, date_str=None):
    """
    Convert a podcast episode title to a filesystem-friendly filename,
    prepending the date in the format (YYYY-MM-DD) if provided.
    """
    # Remove characters that are not allowed in filenames
    sanitized_title = re.sub(r'[\\/*?:"<>|]', '', title)

    # Replace spaces with underscores for readability
    sanitized_title = sanitized_title.replace(' ', '_').lower()

    # Prepend date in the specified format if provided
    if date_str:
        try:
            date = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z')
            date_formatted = date.strftime('%Y-%m-%d')
            sanitized_title = f'{date_formatted}_{sanitized_title}'
        except ValueError as e:
            logging.error(f"Error parsing date: {e}")

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

def parse_and_download(content, save_dir, save_text):
    """Parse the RSS feed and download files."""
    feed = feedparser.parse(content)

    # Count total audio files
    total_audio_files = sum(1 for entry in feed.entries if any(link.type == 'audio/mpeg' for link in entry.get('links', [])))
    logging.info(f"Total audio files to download: {total_audio_files}")

    audio_file_counter = 0
    successful_downloads = 0
    for entry in feed.entries:
        if 'links' in entry:
            for link in entry.links:
                if link.type == 'audio/mpeg':
                    audio_file_counter += 1
                    date_str = entry.get('published', None)
                    title = sanitize_title(entry.title, date_str)

                    # Parse URL for file extension / remove Query String, etc.
                    parsed_url = urlparse(unquote(link.href))
                    _, file_extension = os.path.splitext(parsed_url.path)
                    filename = os.path.join(save_dir, title + file_extension)

                    # Attempt to download the file
                    if download_file(link.href, filename):
                        successful_downloads += 1
                        if save_text:
                            logging.info(f"Saving additional details in text file {filename}")
                            save_text_file(entry, filename)
                    logging.info(f"Downloading audio file {audio_file_counter} of {total_audio_files}")
                    logging.info("Sleeping for 1 second...")
                    time.sleep(1)
    logging.info("Completed! Successfully downloaded {} / {} audio files".format(successful_downloads, total_audio_files))

def main():
    parser = argparse.ArgumentParser(description='RSS Podcast Downloader')
    parser.add_argument('rss_url', help='RSS feed URL (Include authentication token if applicable)')
    parser.add_argument('save_dir', help='Directory to save downloaded files')
    parser.add_argument('--save_text', action='store_true', help='Flag to save text files with extra episode data')
    args = parser.parse_args()

    content = fetch_rss_feed(args.rss_url)
    if content:
        parse_and_download(content, args.save_dir, args.save_text)

if __name__ == "__main__":
    main()
