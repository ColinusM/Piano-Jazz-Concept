# Changelog

All notable changes to Piano Jazz Concept will be documented in this file.

## 2025-10-19

### Feature Additions
- Add brain button (🧠) for per-video song extraction in admin mode (99884f6)
- Add auto-update button to refresh catalog with latest YouTube videos (445975d)
- Auto-update now re-extracts songs for videos with 0 songs (e46b9e7)

### Bug Fixes
- Fix deleted songs appearing after refresh (f3f6eb4)
- Fix OpenAI API key newline issue on Render causing API call failures (b12cfc8)
- Fix auto-update LLM extraction prompt on Render (1b133dc)

### Improvements
- Clarify LLM extraction: title IS the song when formatted with composer/artist (1f37476)
- Improve LLM extraction to handle TV themes and clear song titles (959a1fa)
- Add update logging to track song edits (f3f6eb4)
- Add API key verification logging at startup (99884f6)

### UI/UX Improvements
- Remove duplicate YouTube button and make thumbnail link to YouTube (2cfbdef)

## 2025-10-02

### Bug Fixes
- Fix changelog path to use uppercase CHANGELOG.md (e549679)

### UI/UX Improvements
- Update notification bell to read hierarchical changelog format (fa13845)
- Make notification bell visible to all users (2341bf9)
- Disable auto-login for production (c59fdd8)
- Add notification bell system for admin updates (19ce16e)
- Add Piano Jazz Concept logo overlay to header (88f074f)
- Change pinkish colors to sober grey tones (a27c5a1)
- Change admin login button from fixed to absolute positioning (8c2053a)
- Make search bar and alphabet navigation sticky (a94b8f6)
- Update YouTube button styling to match logo design (0724e4e)
- Make filter links always underlined (8b52ca3)
- Fix banner image to fill full width with proper sizing (1da3fae)

### Feature Additions
- Add login/logout system with Remember Me functionality (8437e18)

### Feature Removals
- Remove 'Tous types' filter from UI and backend (a4d3417)
- Remove sorting controls (Alphabétique, Thématique, Date) (cafb19e)
- Remove performance mode toggle and functionality (0bcd7f3)
- Remove rainbow animations from all buttons (5cca558)
- Remove video type dropdown from UI and backend (b948c8c)
- Remove AI analysis features from UI and backend (1e030c4)

### UI Reorganization
- Reorganize controls layout: separate primary buttons from filters (bda6eaf)
- Rename button from "YouTube Videos" to "Videos" (794b237)

## 2025-10-01

### Major Features
- Add Real Book-style index view for song catalog (c0df477)
- Add clickable filters for metadata fields and category badge (cdebfca)
- Add auto-scroll to cards when clicking index icon (efbe129)
- Add index view with clickable icons and YouTube links (179cde1)
- Add category editing with dropdown for songs and videos (7f55ef4)

### Bug Fixes
- Fix edit functionality for clickable filter fields (06ef6a4)
- Fix index view to enforce single-line entries with text truncation (d2297b8)
- Fix GPT-5 parameter: max_tokens → max_completion_tokens (790490f)

### Infrastructure
- Secure API keys: move to environment variables (8e34038)
- Add gunicorn config with 120s timeout for LLM API calls (213d8c0)
- Add persistent disk support for Render deployment (44bb2fe)
- Add auto-migration for category columns (79f765e)

### LLM/AI Improvements
- Upgrade to GPT-5-mini for better song metadata extraction (499cb3b)
- Revert to GPT-4o-mini for faster extraction (4954f25)
- Remove temperature parameter for GPT-5 compatibility (d65a95c)
- Increase max_tokens and add better error handling for re-extraction (1458288)

### UI Improvements
- Add mobile support for edit icons (6e0b5b4)
- Simplify index view: remove letter headers, add clickable song links (2a05d32)

### Documentation
- Update README with additional links (b3bd47f)
- Update README with deployed site link (36ec3bc)

## 2025-09-30

### Major Features
- Enrich database with LLM-extracted song metadata (177 songs from 193 videos) (6fce452)
- Add comprehensive French README with project documentation (e48367d)
- Add song deletion functionality with undo support (5302c20)
- Add performance mode with low-resolution thumbnails (4940d37)
- Add alphabet navigation and back-to-top button (518335f)
- Add video type categorization feature (dfeab34)
- Add admin mode with inline editing and undo functionality (8b8c3ab)

### UI/UX Redesign
- Redesign UI to match Piano Jazz Concept website aesthetic (2b4cd28)
- Convert all UI colors to minimal grey/white scheme (400b998)
- Integrate Piano Jazz Concept website header banner (2428436)
- Change Master Prompt Editor and search bar backgrounds from black to white (925de3f)
- Make re-extract and get transcript buttons more compact and minimalist (50d84ba)

### Video & Playback Features
- Add inline video playback functionality with clickable thumbnails (65cd4b0)
- Add minimalist YouTube button below thumbnails, update button text, and add favicon (c7e460d)
- Add YouTube thumbnail display to video cards (d3b6b0a)
- Add video_type filtering for YouTube Videos view (11063a9)
- Keep original video title in YouTube Videos view (fb77979)
- Fix video title display in videos view and add YouTube/favicon icons (0a9effa)

### LLM & Extraction Features
- Add collapsible Master Prompt Editor with minimize button (fea8355)
- Add per-video prompt guidance and master prompt editor (056892b)
- Add per-video re-extraction with fixed conservative prompt (a0a78f0)
- Implement super-prompt with comprehensive metadata extraction (60167de)
- Add super-prompt specification for comprehensive LLM enrichment (b4626a0)
- Add Show All Videos button and transcript feature, update documentation (d1fc509)
- Add hover tooltips to LLM extraction UI and enable inline editing for all metadata fields (f63e466)

### Database & Backend
- Update database with latest changes (d06504b)
- Update database with latest video and song data (05345dc, dcc05e1)
- Add plus button to video cards for creating song entries (29a5493)
- Add openai and youtube-transcript-api to requirements.txt (9109cd5)
- Simplify app to read only from songs table (no JOIN) (f90a838)
- Add filtering by enriched metadata and complete LLM enrichment (7d2597c)
- Improve LLM enrichment with smart context-aware matching (1daad9e)
- Update app to display LLM-enriched metadata (0e503ab)
- Reorganize project structure and add LLM enrichment (6b6b615)

### Bug Fixes & Improvements
- Fix Show All Songs crash and add re-extraction debug logging (343e262)
- Fix video view to display extracted song metadata after re-extraction (9c8631c)
- Fix counter label to show 'vidéo(s)' when viewing videos (4fb77d0)
- Fix Show All Videos button to display full video list (7ca3bd7)
- Fix transcript API to use object attributes instead of dict keys (0e4c006)
- Improve song extraction with better artist detection (0e74c63)

### UI Text & Styling
- Display song title as main header in song view mode (020fe3e)
- Update UI text with proper French grammar and compact placeholder (eea7f0d)
- Refine rainbow button styling with subtle animation and centered layout (2fd7c37)
- Add minimalist save notification for video type categorization (1d1cb4c)

### Documentation & Organization
- Add song cross-linking to video cards and enhance documentation (8881142)
- Document admin features and add critical server restart reminder (7d8d650)
- Add documentation on LLM enrichment issues and strategy (ddf59c1)
- Prepare for deployment - add requirements.txt and production config (48c4dab)

### Filtering & Navigation
- Sync filter dropdown with video type categories and add Show All Songs button (e87df23)
- Add video type filter and expandable descriptions (d60f7f5)

### Core Architecture
- Display individual songs instead of videos with Part X/Y badges (ba0eef1)
- Add full description scraping and song analysis tools (d9b59d7)
- Initial commit: Piano Jazz Concept video catalog (2976bf2)

---

## Summary Statistics

- **Total commits**: 93
- **Development period**: September 30 - October 2, 2025
- **Major milestones**:
  - Initial video catalog creation
  - LLM-powered song metadata extraction
  - Admin features with inline editing
  - Real Book-style index view
  - Complete UI redesign matching Piano Jazz Concept branding
  - Production deployment with security hardening
