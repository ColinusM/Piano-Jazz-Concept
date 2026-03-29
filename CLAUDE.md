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

### YouTube Transcript Fetching (Rate Limits)

Use the `youtube-transcript-api` Python package to fetch video transcripts when title/description are ambiguous:
```python
from youtube_transcript_api import YouTubeTranscriptApi
api = YouTubeTranscriptApi()
transcript = api.fetch('VIDEO_ID', languages=['fr', 'en'])
```

**RATE LIMIT WARNING:** YouTube blocks IPs that make too many transcript requests. There is no published exact threshold — it depends on IP reputation and request patterns. Typical behavior:
- **Residential IPs** (like Colin's home connection) can handle ~10-20 requests before risking a temporary block
- **Cloud provider IPs** are blocked almost immediately
- Blocks are temporary (usually lift within a few hours)
- **Always add 2-3 second delays** between transcript fetches: `import time; time.sleep(3)`
- **Batch carefully:** When processing many videos, do transcript fetches in small batches (5-10 at a time), not all at once
- **Fallback:** If transcripts are blocked, use web searches or Chrome DevTools MCP to check video content instead

### Extraction Logic (applies to both methods)
- Read the video title + description + transcript (when available)
- Identify which songs/pieces are analyzed in the video
- NEVER list Étienne Guéreau as performer — he's the analyst/demonstrator, not the artist
- **EXCEPTION:** For Étienne's OWN compositions (FLING album, etc.), list him as BOTH composer AND performer
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

**MANDATORY: Tag `analysis_depth` on EVERY new song.** After inserting songs, you MUST update the `analysis_depth` field for each one:
- **`Théorie`** = Full musical/harmonic analysis (the video deeply analyzes the song's harmony, melody, arrangement, etc.)
- **`Mention`** = Song is mentioned, performed, or referenced but not deeply analyzed (editorial, reaction, Étienne's own performances, cultural discussion, plagiarism comparison, etc.)

```sql
UPDATE songs SET analysis_depth = 'Théorie' WHERE id = ?;
-- or
UPDATE songs SET analysis_depth = 'Mention' WHERE id = ?;
```
Never leave `analysis_depth` as NULL. This field drives the color-coding in the UI (green = Théorie, blue = Mention).

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
- **Videos view** (`/?view=videos`) — Shows video cards with extracted songs underneath (available to all users)
- **Index view** (`/?view=index`) — Real Book-style alphabetical list of songs
- **Sort:** Default is `sort=date` (newest first). Toggle to `sort=alpha` for A-Z.

Templates:
- `templates/index.html` (2106 lines) — Main catalog with cards, filters, admin features
- `templates/index_view.html` (214 lines) — Real Book alphabetical index
- `templates/login.html` (179 lines) — Admin login page

## Deployment

- Hosted on **PythonAnywhere** — https://pianojazzconcept.pythonanywhere.com/
- Database at `database/piano_jazz_videos.db` locally
- GitHub repo: `ColinusM/Piano-Jazz-Concept`

### PythonAnywhere Setup Details
- **Account:** PianoJazzConcept (free tier)
- **Python:** 3.10
- **Virtualenv:** `/home/PianoJazzConcept/.virtualenvs/pjc`
- **Source directory:** `/home/PianoJazzConcept/Piano-Jazz-Concept`
- **WSGI file:** `/var/www/pianojazzconcept_pythonanywhere_com_wsgi.py`
- **Static files:** URL `/static` → `/home/PianoJazzConcept/Piano-Jazz-Concept/static`
- **Free tier limit:** Must click "extend" once per month (email reminder sent). No CPU limit on web app itself.

### How to Deploy to Production (NO API TOKEN NEEDED)

Deploy by navigating to the PythonAnywhere webapp page in Chrome (via Chrome DevTools MCP) and using the PythonAnywhere REST API with the CSRF token from the browser cookie. **No API token is required.**

**Step 1 — Navigate to PythonAnywhere in Chrome:**
```
Navigate to: https://www.pythonanywhere.com/user/PianoJazzConcept/webapps/
If logged out, click the "Log in" button (credentials are pre-filled in Chrome).
```

**Step 2 — Upload changed files from GitHub and reload (run as JS in Chrome):**
```javascript
// Run this via mcp__chrome-devtools__evaluate_script
async () => {
  const csrf = document.cookie.match(/csrftoken=([^;]+)/)[1];
  const h = {'X-CSRFToken': csrf};

  // List ALL files that changed (adjust this list per deploy)
  const files = ['app.py', 'templates/index.html', 'database/piano_jazz_videos.db'];

  for (const file of files) {
    const resp = await fetch(`https://raw.githubusercontent.com/ColinusM/Piano-Jazz-Concept/main/${file}`);
    const blob = await resp.blob();
    const fd = new FormData();
    fd.append('content', blob, file.split('/').pop());
    const path = `/api/v0/user/PianoJazzConcept/files/path/home/PianoJazzConcept/Piano-Jazz-Concept/${file}`;
    // DELETE first to bust cache, then re-upload (see post-mortem)
    await fetch(path, {method: 'DELETE', headers: h});
    await fetch(path, {method: 'POST', headers: h, body: fd});
  }

  // Reload the web app
  await fetch('/api/v0/user/PianoJazzConcept/webapps/PianoJazzConcept.pythonanywhere.com/reload/', {
    method: 'POST', headers: h
  });

  return 'deployed';
}
```

**Step 3 — Verify:**
```bash
curl -s "https://pianojazzconcept.pythonanywhere.com/" | grep -o '[0-9]* morceaux trouvés'
```

### Deploy Workflow Summary
1. Make changes locally
2. `git add <files> && git commit -m "message" && git push`
3. Open Chrome to PythonAnywhere webapps page (login if needed — creds are pre-filled)
4. Run the JS snippet above via `mcp__chrome-devtools__evaluate_script` to pull from GitHub and reload
5. Verify with curl
6. Open the production site in Chrome — if no tab with `pianojazzconcept.pythonanywhere.com` is already open, use `mcp__chrome-devtools__new_page` to open `https://pianojazzconcept.pythonanywhere.com/` so the user can see the result immediately

### Chrome DevTools MCP Notes
- Chrome DevTools MCP v0.20+ uses **autoConnect** — no debug port needed, just run Chrome normally
- One-time setup: go to `chrome://inspect/#remote-debugging` in Chrome and enable the toggle
- If session expires, navigate to PythonAnywhere login page — username and password are pre-filled, just click "Log in"
- If CSRF cookie error (`Cannot read properties of null`), navigate to PythonAnywhere first to get a fresh cookie
- See `.claude/rules/chrome-mcp.md` for full MCP setup details


**Issue:** When making metadata fields (composer, performer, style, era) clickable for filtering, the inline edit functionality broke.

**Symptoms:**
- Clicking the ✏️ edit icon would make the text disappear
- No input box would appear
- Unable to edit the field


**Key Lesson:** When wrapping editable elements in interactive containers (links, buttons), ensure the JavaScript that manipulates them is aware of the container and targets it appropriately for visibility changes.


**Post-mortem: PythonAnywhere file caching causes stale deploys (2026-03-25)**

**Issue:** After uploading a fixed `index.html` via the PythonAnywhere file API (`POST /api/v0/.../files/path/...`), the web app continued serving the old broken version, causing a persistent 500 error (Jinja `TemplateSyntaxError`).

**Root cause:** PythonAnywhere's file API `POST` (overwrite) does not always invalidate the cached version of the file. The web app reload (`POST .../reload/`) restarts the WSGI process, but it may still read the old file from disk cache.

**Fix:** **DELETE the file first, then re-upload it**, then reload:
```javascript
// Inside the deploy JS snippet:
await fetch('/api/v0/user/PianoJazzConcept/files/path/home/PianoJazzConcept/Piano-Jazz-Concept/templates/index.html', {method: 'DELETE', headers: h});
// Then POST the new file
// Then reload the webapp
```

**Key Lesson:** When deploying to PythonAnywhere via the file API, always DELETE then re-upload rather than just overwriting. This ensures the cached file is invalidated. Update the deploy JS snippet accordingly.


**Post-mortem: INSERT OR REPLACE breaks song thumbnails (2026-03-29)**

**Issue:** 155 out of 299 song cards had missing thumbnails on production.

**Root cause:** `utils/scrape_youtube.py` used `INSERT OR REPLACE INTO videos`. SQLite's REPLACE deletes the old row and inserts a new one with a **new auto-increment `id`**. Since `songs.video_id` is a FK to `videos.id`, all songs referencing the old ID became orphaned — the JOIN to get `thumbnail_url` returned NULL.

**Fix:**
1. Re-mapped all 155 broken `songs.video_id` values using `video_url` matching: `UPDATE songs SET video_id = (SELECT id FROM videos WHERE url = songs.video_url)`
2. Changed the scrape script to `INSERT OR IGNORE` + `UPDATE ... WHERE video_id=?` to preserve existing row IDs.

**Key Lesson:** Never use `INSERT OR REPLACE` on tables with auto-increment IDs that are referenced as foreign keys. Use `INSERT OR IGNORE` + `UPDATE` instead.



**CRITICAL:** When the user says "ready to push", you MUST:

1. **Commit all current changes** with descriptive message
2. **Read git log** from HEAD back to the last changelog.md edit to find all uncommitted-to-changelog commits
3. **Update changelog.md** in NON-TECHNICAL language (the reader is Étienne, a musician, NOT a developer):
   - Group by date
   - Categorize appropriately (Nouveaux morceaux, Améliorations, Corrections, etc.)
   - **STRICTLY FORBIDDEN words/concepts:** CSS, HTML, JavaScript, API, architecture, refonte, cache, navigateur, fichier séparé, WSGI, Flask, template, endpoint, maintenabilité, performance technique, positionnement, fixed/absolute, z-index, commit, deploy, migration, base de données, SQL, requête
   - NO commit hashes, NO technical jargon, NO code references, NO implementation details
   - Write as if explaining to someone who has NEVER seen a line of code: describe only the VISIBLE result
   - **GOOD examples:** "Le site se charge plus vite", "Les boutons sont maintenant à gauche dans le bandeau", "Le panneau de notifications ne déborde plus de l'écran"
   - **BAD examples:** "Refonte de l'architecture", "Le CSS est dans un fichier séparé", "Position fixed au lieu de absolute", "Cache du navigateur optimisé"
   - Focus ONLY on WHAT changed visually or functionally for the user, NEVER on HOW it was implemented
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