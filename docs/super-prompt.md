# Super-Prompt for LLM Enrichment

## Context
Piano Jazz Concept is Étienne Guéreau's YouTube channel where he analyzes jazz music. The goal is to catalog EVERY song/piece that has been analyzed on the channel, so viewers can find what's already been covered.

## Core Rules

1. **NEVER list Étienne Guéreau as performer** - he's the YouTuber/analyst, not the artist being cataloged
2. **Extract performer from context** (title, description) OR use your training data
3. **Use your full knowledge base** - if you know the song, add ALL relevant info
4. **Multiple versions = multiple entries** - if comparing Coltrane vs Rollins, create 2 separate song entries
5. **Extract EVERYTHING** - no limitations on metadata

## Super-Prompt Template

```
You are analyzing a Piano Jazz Concept YouTube video to catalog which songs/pieces have been analyzed.

VIDEO TITLE: {title}
VIDEO URL: {url}
FULL DESCRIPTION: {description}

CRITICAL CONTEXT:
- Piano Jazz Concept is Étienne Guéreau's educational channel
- NEVER list Étienne as "performer" - he's the analyst/demonstrator
- Focus on WHICH ARTISTS' RECORDINGS are being analyzed/discussed
- If title says "avec Brad Mehldau" → Brad is the featured performer
- If analyzing "Coltrane's Giant Steps" → Coltrane is the performer
- If just "Giant Steps" with no artist → use your knowledge (original = John Coltrane)
- If comparing multiple artists' versions → create SEPARATE entries for each

YOUR TASK:
Extract ALL songs/pieces analyzed in this video with MAXIMUM metadata:

For each song, use:
1. Video title/description to identify songs and artists
2. Your training data to fill gaps and add context
3. Your knowledge of jazz history, famous recordings, albums, etc.

EXTRACT EVERYTHING:
- Song title
- Composer(s)
- Performer/Artist (whose recording/version is being analyzed)
  - From title: "avec Brad Mehldau" → Brad Mehldau
  - From description: "analyse du solo de Coltrane" → John Coltrane
  - From your knowledge: "Giant Steps" → John Coltrane (if not specified)
- Original artist (if it's a cover/arrangement)
- Album name (if mentioned OR if you know which famous album)
- Record label (if you know it)
- Recording year (if mentioned OR if you know the famous recording year)
- Composition year
- Style/genre
- Era/decade
- All featured artists mentioned in title/description
- Context notes (is this analyzing a specific recording? comparing versions?)
- Timestamp (if provided in description)

MULTIPLE VERSIONS:
If video compares/analyzes multiple artists' versions of same song, create SEPARATE entries:
- "Giant Steps: Coltrane vs Tommy Flanagan" → 2 entries (one for each artist)

NO LIMITATIONS:
Add as much information as you can from your training data. If you know the song, share:
- Famous recordings and their details
- Historical context
- Notable musicians on the recording
- Anything relevant to cataloging this analysis

Return JSON array. Even if single song, return array with 1+ items:
[
  {
    "song_title": "song name",
    "composer": "who wrote it",
    "performer": "whose recording is analyzed (NEVER Étienne)",
    "original_artist": "if it's a cover",
    "album": "album name if known",
    "record_label": "label if known",
    "recording_year": year or null,
    "composition_year": year or null,
    "style": "genre/style",
    "era": "decade/era",
    "featured_artists": ["all", "artists", "mentioned"],
    "timestamp": "MM:SS or null",
    "context_notes": "any relevant context about this analysis",
    "additional_info": "anything else valuable"
  }
]

Be comprehensive! Use both the video content AND your training knowledge.
```

## Examples

### Example 1: Brad Mehldau Video
**Input:**
- Title: "L'art de jouer diatonique avec Brad Mehldau et Charlie Haden"
- Description: "Après un chorus magistral de Brad, Charlie Haden déploie ses talents..."

**Expected Output:**
```json
[
  {
    "song_title": "America The Beautiful",
    "composer": "Samuel A. Ward",
    "performer": "Brad Mehldau",
    "original_artist": "Katharine Lee Bates (lyrics)",
    "album": "Live in Tokyo",
    "recording_year": 2004,
    "composition_year": 1893,
    "style": "Jazz",
    "era": "2000s",
    "featured_artists": ["Brad Mehldau", "Charlie Haden"],
    "context_notes": "Analysis of Brad Mehldau's performance with Charlie Haden on bass"
  }
]
```

### Example 2: Comparison Video
**Input:**
- Title: "Giant Steps: Coltrane vs Tommy Flanagan"

**Expected Output:** 2 entries
```json
[
  {
    "song_title": "Giant Steps",
    "composer": "John Coltrane",
    "performer": "John Coltrane",
    "album": "Giant Steps",
    "record_label": "Atlantic",
    "recording_year": 1959,
    "composition_year": 1959,
    "style": "Bebop/Hard Bop",
    "era": "1950s"
  },
  {
    "song_title": "Giant Steps",
    "composer": "John Coltrane",
    "performer": "Tommy Flanagan",
    "album": "Giant Steps",
    "recording_year": 1959,
    "style": "Bebop/Hard Bop",
    "era": "1950s",
    "context_notes": "Tommy Flanagan on piano for Coltrane's original recording"
  }
]
```

### Example 3: No Artist Mentioned
**Input:**
- Title: "Les substitutions tritoniques"
- Description: "Analyse de All The Things You Are..."

**Expected Output:**
```json
[
  {
    "song_title": "All The Things You Are",
    "composer": "Jerome Kern",
    "performer": null,
    "original_artist": "Jerome Kern",
    "composition_year": 1939,
    "style": "Jazz Standard",
    "era": "1930s",
    "context_notes": "Theoretical analysis, no specific recording mentioned"
  }
]
```

## Implementation Notes

- Strip markdown code blocks from LLM response before parsing
- Handle theory videos that don't specify recordings (performer = null)
- Validate JSON before inserting to database
- Log all extraction attempts for review