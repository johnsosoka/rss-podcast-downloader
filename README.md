# RSS Podcast Downloader

A powerful and flexible Python script to download, manage, and archive podcast episodes from any RSS feed.

## Description

`RSS Podcast Downloader` is a robust tool for downloading podcasts from any given RSS feed. It is designed to be a "set it and forget it" solution, with features that support resuming downloads and tracking your library across multiple podcast feeds.

The script creates clean, portable filenames and can enrich your media library by automatically writing episode metadata (like title, album, and artist) to the downloaded MP3 files.

A local SQLite database (`downloads.db`) is created in the script's directory to keep track of all downloaded episodes, preventing duplicates and allowing you to manage podcasts from multiple feeds seamlessly.

## Features

- **Download Resuming**: Automatically tracks downloaded episodes in a local database and skips them on subsequent runs.
- **Multi-Feed Support**: Tracks episodes from multiple RSS feeds independently.
- **MP3 Tagging**: Automatically writes ID3 metadata (Title, Album, Artist, Date, Genre, etc.) to downloaded MP3 files.
- **Download Limiting**: Use the `--num-episodes` flag to check only the latest `N` episodes for anything new.
- **Smart Filename Sanitization**: Converts episode titles into clean, ASCII-only, filesystem-friendly filenames.
- **Save Episode Details**: Optionally save episode summaries in a separate text file.
- **Command-Line Interface**: Simple CLI for specifying the RSS feed URL and save directory.
- **Error Handling**: Provides clear error messages and retry logic for downloads.

## Filename Convention

The script generates filenames with a clean, consistent, and sortable convention:

```text
YYYY-MM-DD_lowercase_and_ascii_title.mp3
```
The prepended date is the publication date of the podcast episode.

## Requirements

- Python 3.x
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/johnsosoka/rss-podcast-downloader.git
   cd rss-podcast-downloader
   ```
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

The script requires the RSS feed URL and a directory to save the downloaded files.

```bash
python rss-podcast-downloader.py <RSS_FEED_URL> <SAVE_DIRECTORY> [OPTIONS]
```

### Arguments

- `<RSS_FEED_URL>`: The URL of the podcast's RSS feed. (Required)
- `<SAVE_DIRECTORY>`: The local directory where podcast files will be saved. (Required)

### Options

- `--num-episodes <N>`: Check only the `<N>` most recent episodes in the feed for new downloads. This is useful for quickly syncing the latest episodes without checking the entire feed history.
- `--save_text`: Flag to save additional episode details (like the summary) in a separate `.txt` file alongside the audio file.

## Examples

**Initial Run: Download all episodes for a podcast**
```bash
python rss-podcast-downloader.py "http://example.com/podcast.rss" "./podcasts/MyShow"
```

**Daily Sync: Check for the 5 latest episodes and download any that are missing**
```bash
python rss-podcast-downloader.py "http://example.com/podcast.rss" "./podcasts/MyShow" --num-episodes 5
```

**Sync and Save Text Files**
```bash
python rss-podcast-downloader.py "http://another-feed.com/rss" "./podcasts/AnotherShow" --save_text
```
