# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Piano Jazz Concept Video Catalog - A Flask web application that indexes and displays YouTube videos from the **Piano Jazz Concept** YouTube channel (run by **Étienne Guéreau**). The app scrapes video data, extracts individual songs from compilation videos, and provides a searchable, categorized interface.

**This is a client project** — Colin (the developer) builds and maintains this for free. Étienne is the channel owner, not the developer.

## CRITICAL: Videos vs Songs

**NEVER confuse VIDEOS with SONGS:**

- **VIDEOS** = Raw YouTube videos scraped from the channel (stored in `videos` table)
  - ~197 videos as of Oct 2025
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

**CRITICAL: After ANY code edit (app.py, templates/, etc.), you MUST restart the Flask server for changes to take effect. The user needs to see changes immediately.**

To restart:
```bash
# Kill existing Flask process and restart
lsof -ti:5000 | xargs kill -9 2>/dev/null && python -u app.py 2>&1 | tee -a /tmp/flask.log
```

**IMPORTANT: Check for background processes.** There are often multiple Flask processes running. Before restarting, verify which shell IDs are active. Kill all competing processes to avoid port conflicts.

## Data Pipeline

The application follows a multi-step data pipeline:

### Step 1 — Scrape YouTube Videos
`cd utils && python scrape_youtube.py`
- Fetches all videos from the Piano Jazz Concept YouTube channel using YouTube Data API v3 (free tier)
- Creates/updates the `videos` table in the database
- Must be run from the `utils/` directory due to relative path `../database/piano_jazz_videos.db`
- API key stored in `.env` as `YOUTUBE_API_KEY`

### Step 2 — Extract Songs from Videos (TWO METHODS)

**Method A — Claude Code CLI (PREFERRED, free):**
- When working in Claude Code, Claude analyzes each new video's title + description directly in the conversation
- Uses web searches when needed to identify songs, composers, performers, albums, etc.
- Inserts song rows directly into SQLite via shell commands
- No API cost — runs through the Claude Code subscription
- This is the current preferred method since there is no OpenAI budget

**Method B — OpenAI API (legacy, costs money):**
- `cd utils && python llm_full_extract.py`
- Uses OpenAI GPT-4o-mini to analyze video titles/descriptions
- Requires `OPENAI_API_KEY` in `.env` — currently no budget for this
- Only use if OpenAI budget becomes available again

### Step 3 — Optional: Count Songs
`cd utils && python count_songs.py` — Utility script to get statistics on the database

### Extraction Logic (applies to both methods)
- Read the video title + description
- Identify which songs/pieces are analyzed in the video
- NEVER list Étienne Guéreau as performer — he's the analyst/demonstrator, not the artist
- If a video analyzes multiple songs → create one song row per song
- If a video is pure theory with no specific songs → create 0 song rows
- Extract: song_title, composer, performer, original_artist, album, record_label, recording_year, composition_year, style, era, featured_artists, context_notes, timestamp
- Titles formatted as "Song Title (Composer)" or "Title | Artist" → the title IS the song

### Song INSERT Template
```sql
INSERT INTO songs (
    video_id, song_title, composer, performer,
    original_artist, timestamp, composition_year,
    style, era, additional_info,
    part_number, total_parts,
    album, record_label, recording_year,
    featured_artists, context_notes,
    video_title, video_url, video_description, published_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```
- `video_id` = the `id` column from the `videos` table (NOT the YouTube video_id string)
- `featured_artists` = JSON string like `["Artist1", "Artist2"]`
- `published_at` = copy from the video's `published_at` field

## Architecture

### Database Schema

SQLite database at `database/piano_jazz_videos.db` with two main tables:

**videos table:**
- Stores raw YouTube video metadata
- Fields: id, video_id (YouTube ID string), title, description, url, published_at, thumbnail_url, video_type, category

**songs table:**
- Stores individual songs/pieces analyzed in videos (extracted via LLM from video titles/descriptions)
- Fields: id, video_id (FK → videos.id), song_title, composer, performer, original_artist, album, record_label, recording_year, composition_year, style, era, featured_artists, context_notes, timestamp, part_number, total_parts, video_title, video_url, video_description, published_at, additional_info, songwriters, other_musicians, data_source, deleted (soft delete flag), category
- One video can produce 0, 1, or many song entries
- Videos with multiple songs have same video_id but different part_numbers
- Videos with no specific songs analyzed = 0 entries in songs table
- Soft deletes: deleted=1 hides from UI, deleted=0 or NULL shows

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

## Admin Features

The application includes admin mode with enhanced features (requires login via `config/admin_config.py`):


### Per-Song Management
Each song card in admin mode includes:
- **Inline editing**: Click ✏️ icon to edit any field (composer, performer, style, etc.)
  - Editable fields defined in `app.py:366-368` (allowed_fields list)
  - Updates saved to database via `/api/update_song` endpoint
- **Undo functionality**: Cmd+Z or click undo notification to revert last change
- **Prompt guidance field**: Add extraction hints before re-extracting (e.g., "focus on solos")
- **Re-extract button**: Re-run LLM extraction for specific video with optional guidance
  - Uses same prompt as `llm_full_extract.py` (see `app.py:456-534`)
  - Deletes old songs and inserts new extractions
- **Get Transcript button**: Fetch YouTube transcript (French/English with fallback) for analysis
  - Implementation in `app.py:612-667`

### Filtering and Display
- **Show All Videos button**: Resets all filters to display complete song catalog
- Multiple filter dropdowns: category, type, composer, performer, style, era
- Search bar for text-based filtering
- Sort options: alphabetical, thematic, or by date

## YouTube API Configuration

The API key is loaded from `.env` (`YOUTUBE_API_KEY`). The channel handle is set to 'Pianojazzconcept' in `utils/scrape_youtube.py`. When updating API credentials, also check the `config/` directory for OAuth client secrets.

## Views & Templates

The app has 3 view modes:
- **Songs view** (default, `/?view=songs`) — Shows song cards from `songs` table, filterable by category/composer/style/etc.
- **Videos view** (admin only, `/?view=videos`) — Shows video cards with extracted songs underneath
- **Index view** (`/?view=index`) — Real Book-style alphabetical list of songs

Templates:
- `templates/index.html` (2106 lines) — Main catalog with cards, filters, admin features
- `templates/index_view.html` (214 lines) — Real Book alphabetical index
- `templates/login.html` (179 lines) — Admin login page

## Deployment

- Hosted on **Render** (web service)
- Uses **Gunicorn** in production (`gunicorn.conf.py`)
- Database persisted at `/data/piano_jazz_videos.db` on Render, `database/piano_jazz_videos.db` locally
- GitHub repo: `ColinusM/Piano-Jazz-Concept`


**Issue:** When making metadata fields (composer, performer, style, era) clickable for filtering, the inline edit functionality broke.

**Symptoms:**
- Clicking the ✏️ edit icon would make the text disappear
- No input box would appear
- Unable to edit the field


**Key Lesson:** When wrapping editable elements in interactive containers (links, buttons), ensure the JavaScript that manipulates them is aware of the container and targets it appropriately for visibility changes.





**CRITICAL:** When the user says "ready to push", you MUST:

1. **Commit all current changes** with descriptive message
2. **Read git log** from HEAD back to the last changelog.md edit to find all uncommitted-to-changelog commits
3. **Update changelog.md** with ALL those commits in hierarchical format:
   - Group by date
   - Categorize appropriately
   - Include all commit hashes
   - Add at the TOP of the file
4. **Commit the changelog update**
5. **Push to remote** with `git push`

**Example workflow:**
```bash
# User says: "ready to push"

# 1. Commit current changes
git add .
git commit -m "Update notification bell styling"

# 2. Find commits since last changelog edit
git log --oneline --until="$(git log -1 --format=%ai -- changelog.md)" HEAD

# 3. Update changelog.md at TOP with all commits grouped by date and category

# 4. Commit changelog
git add changelog.md
git commit -m "Update changelog with recent commits"

# 5. Push
git push
```

This ensures the changelog is always up-to-date before pushing to remote.