# RSS Podcast Downloader

This Python script downloads audio files and accompanying text information from specified RSS feeds. It was quickly
developed to download the complete archive of the [The Last Podcast on the Left](https://www.lastpodcastontheleft.com/)
collection from their Patreon RSS feed...It has not been tested extensively, but it _should_ work for most RSS feeds.

## Description

`RSS Podcast Downloader` is a tool for downloading podcasts from any given RSS feed. It not only fetches audio files but also allows the option to save additional episode details in a text file, ensuring a comprehensive podcast experience.

It will only download podcast entries that are published with the link type, `audio/mpeg`. Furthermore, at this time


The filenames have an opinionated convention and are based on the following format:

```text
YYYY-MM-DD_lowercase_underbar_delimited_title.xyz
```

The prepended date is the publication date of the podcast episode.

## Features

- **Download Audio Files**: Automatically download audio files from the RSS feed.
- **Save Episode Details**: Optionally save additional episode details in a text file.
- **Filesystem-Friendly Filenames**: Sanitizes titles to create filenames compatible with most filesystems.
- **Command-Line Interface**: Simple CLI for specifying the RSS feed URL and save directory.
- **Error Handling**: Provides clear error messages for common issues like download failures or RSS feed fetching errors.

## Usage

To use this script, you need to provide the RSS feed URL and the directory where the files will be saved. The `--save_text` flag can be used to save additional episode details in a text file.

```bash
python rss-podcast-downloader.py <RSS_FEED_URL> <SAVE_DIRECTORY> [--save_text]
```

## Requirements

- Python 3.x 
- Required Python packages (see requirements.txt)

To install the required packages, run:

```bash
pip install -r requirements.txt
```

## Installation

```commandline
git clone git@github.com:johnsosoka/rss-podcast-downloader.git
cd rss-podcast-downloader
pip install -r requirements.txt
```

## Examples

**Save Audio Files + Text Files with Episode Details**

```bash
python rss-podcast-downloader.py "http://example.com/rss" "./podcasts" --save_text
```

**Save Audio Files Only**

```bash
python rss-podcast-downloader.py "http://example.com/rss" "./podcasts"
```