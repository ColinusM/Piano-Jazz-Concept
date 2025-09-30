# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Piano Jazz Concept Video Catalog - A Flask web application that indexes and displays YouTube videos from the Piano Jazz Concept channel. The app scrapes video data, extracts individual songs from compilation videos, and provides a searchable, categorized interface.

## CRITICAL: Videos vs Songs

**NEVER confuse VIDEOS with SONGS:**

- **VIDEOS** = Raw YouTube videos scraped from the channel (stored in `videos` table)
  - ~193 videos total
  - Each video has: id, video_id, title, description, url, published_at, thumbnail_url

- **SONGS** = Individual songs/pieces analyzed within videos (stored in `songs` table)
  - A video can contain 0, 1, or multiple songs
  - A video analyzing 5 different jazz standards = 5 songs in the songs table
  - A video about jazz theory with no specific songs = 0 songs in the songs table
  - Each song references its parent video via `video_id` foreign key

The web interface displays SONGS (not videos), with each song card showing which video it came from.

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

2. **Extract and categorize songs**: `cd utils && python llm_full_extract.py`
   - Uses OpenAI GPT-4o-mini to analyze video titles/descriptions and extract song metadata
   - Extracts: song title, composer, performer, album, recording year, style, era, etc.
   - Creates/updates the `songs` table with LLM-extracted data
   - Must be run from the `utils/` directory
   - This populates the songs table from the videos table (193 videos → ~500+ songs)

3. **Optional - Count songs**: `cd utils && python count_songs.py`
   - Utility script to get statistics on the database

## Architecture

### Database Schema

SQLite database at `database/piano_jazz_videos.db` with two main tables:

**videos table:**
- Stores raw YouTube video metadata
- Fields: id, video_id, title, description, url, published_at

**songs table:**
- Stores individual songs/pieces analyzed in videos (extracted via LLM from video titles/descriptions)
- Fields: id, video_id (FK), song_title, composer, performer, original_artist, album, record_label, recording_year, composition_year, style, era, featured_artists, context_notes, timestamp, part_number, total_parts, video_title, video_url, video_description, published_at
- One video can produce 0, 1, or many song entries
- Videos with multiple songs have same video_id but different part_numbers
- Videos with no specific songs analyzed = 0 entries in songs table

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
  - `scrape_youtube.py` - YouTube API scraper (populates videos table)
  - `llm_full_extract.py` - LLM-based song extraction (populates songs table from videos)
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