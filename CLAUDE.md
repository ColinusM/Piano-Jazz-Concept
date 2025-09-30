# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Piano Jazz Concept Video Catalog - A Flask web application that indexes and displays YouTube videos from the Piano Jazz Concept channel. The app scrapes video data, extracts individual songs from compilation videos, and provides a searchable, categorized interface.

## Running the Application

```bash
# Start the Flask development server
python app.py
```

The app runs on http://127.0.0.1:5000 by default.

## Data Pipeline

The application follows a multi-step data pipeline that must be run in order:

1. **Scrape YouTube data**: `cd utils && python scrape_youtube.py`
   - Fetches all videos from the Piano Jazz Concept YouTube channel using YouTube Data API v3
   - Creates/updates the `videos` table in the database
   - Must be run from the `utils/` directory due to relative path `../database/piano_jazz_videos.db`

2. **Extract and categorize songs**: `cd utils && python create_songs_table.py`
   - Parses video descriptions to extract individual songs with timestamps
   - Distinguishes between compilation videos (3+ segments) and single-song videos
   - Creates/updates the `songs` table with parsed data
   - Must be run from the `utils/` directory

3. **Optional - Count songs**: `cd utils && python count_songs.py`
   - Utility script to get statistics on the database

## Architecture

### Database Schema

SQLite database at `database/piano_jazz_videos.db` with two main tables:

**videos table:**
- Stores raw YouTube video metadata
- Fields: id, video_id, title, description, url, published_at

**songs table:**
- Stores individual songs extracted from video descriptions
- Fields: id, video_id (FK), song_title, composer, timestamp, part_number, total_parts
- Compilation videos have multiple rows with same video_id but different part_numbers
- Single-song videos have total_parts=1

### Video Categorization

The `categorize_video()` function in `app.py:30-59` uses keyword matching to classify videos into categories:
- Génériques TV (TV themes)
- BO Films (Movie soundtracks)
- Chansons/Standards (Songs/Standards)
- Jeux Vidéo (Video games)
- Théorie/Analyse (Theory/Analysis)
- Interviews/Culture
- Autres (Other)

When modifying categories, update the keyword lists in this function.

### Timestamp Handling

Timestamps from video descriptions are automatically converted to YouTube URL parameters (`&t=123s`) in `app.py:76-82`. The conversion assumes MM:SS format and calculates total seconds.

## File Organization

- `app.py` - Main Flask application (run from project root)
- `utils/` - Data pipeline scripts (run from utils/ directory)
  - `scrape_youtube.py` - YouTube API scraper
  - `create_songs_table.py` - Song extraction and parsing
  - `extract_songs.py` - Legacy extraction script
  - `count_songs.py` - Database statistics
- `database/` - SQLite database file
- `config/` - Google API credentials (client_secret JSON)
- `templates/` - Jinja2 HTML templates
- `static/` - Static assets
- `scripts/` - Miscellaneous scripts and logs
- `data/` - Data files and temporary journals

## Important Path Considerations

All utility scripts in `utils/` use relative path `../database/piano_jazz_videos.db` and must be executed from within the `utils/` directory. The main Flask app (`app.py`) uses relative path `database/piano_jazz_videos.db` and must be executed from the project root.

## YouTube API Configuration

The API key is hardcoded in `utils/scrape_youtube.py:6`. The channel handle is set to 'Pianojazzconcept'. When updating API credentials, also check the `config/` directory for OAuth client secrets.