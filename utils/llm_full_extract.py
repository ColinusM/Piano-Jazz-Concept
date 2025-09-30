"""
Complete LLM-based extraction from raw video data.
No pre-parsing - just raw title + description → LLM → structured data.
"""
import sqlite3
import json
from openai import OpenAI

client = OpenAI(
    api_key="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"
)

def extract_video_data(video_title, video_description, video_url):
    """
    Super-prompt: Extract EVERYTHING using title + description + LLM training data.
    """

    prompt = f"""You are analyzing a Piano Jazz Concept YouTube video to catalog which songs/pieces have been analyzed.

VIDEO TITLE: {video_title}
VIDEO URL: {video_url}
FULL DESCRIPTION:
{video_description}

CRITICAL CONTEXT:
- Piano Jazz Concept is Étienne Guéreau's educational jazz channel
- NEVER list Étienne as "performer" - he's the analyst/demonstrator, NOT the artist to catalog
- Focus on WHICH ARTISTS' RECORDINGS are being analyzed/discussed
- If title says "avec Brad Mehldau" → Brad is the featured performer
- If analyzing a specific song/artist clearly → extract that song
- If comparing multiple artists' versions → create SEPARATE entries for each

IMPORTANT - BE CONSERVATIVE:
- ONLY extract songs that are CLEARLY mentioned in title or description
- If video is theory/discussion with NO SPECIFIC SONGS → return empty array []
- DO NOT make up songs or use generic examples
- DO NOT default to any particular song if unclear
- If unsure → return empty array []

YOUR TASK:
Extract ALL songs/pieces analyzed in this video with MAXIMUM metadata.

Use THREE sources:
1. Video title/description to identify songs and artists
2. Your training data to fill gaps and add context
3. Your knowledge of jazz history, famous recordings, albums, etc.

EXTRACT EVERYTHING (but only if songs are clearly present):
- Song title (MUST be explicitly mentioned in title/description)
- Composer(s)
- Performer/Artist (whose recording/version is being analyzed - NEVER Étienne)
  - From title: "avec Brad Mehldau" → Brad Mehldau
  - From description: "analyse du solo de Coltrane" → John Coltrane
  - If song mentioned but no performer → use your knowledge to identify famous version
  - If no specific recording mentioned → leave null
- Original artist (if it's a cover/arrangement)
- Album name (if mentioned OR if you know which famous album)
- Record label (if you know it)
- Recording year (if mentioned OR if you know the famous recording year)
- Composition year
- Style/genre
- Era/decade
- Featured artists (all artists mentioned in title/description)
- Context notes (analyzing specific recording? comparing versions? theory video?)
- Timestamp (if provided)

MULTIPLE VERSIONS:
If video compares/analyzes multiple artists' versions, create SEPARATE entries

NO LIMITATIONS:
Add as much information as you can from your training data. If you know the song:
- Famous recordings and their details
- Historical context
- Notable musicians
- Anything valuable for cataloging

Return JSON array:
- If songs found: return array with song objects
- If NO songs mentioned/analyzed: return empty array []
- Even if single song, return array with 1 item

Example response:
[
  {{
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
    "featured_artists": ["artist1", "artist2"],
    "timestamp": "MM:SS or null",
    "context_notes": "context about this analysis",
    "additional_info": "anything else valuable"
  }}
]

Or if no songs: []

Be comprehensive BUT conservative! Only extract what's actually there."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a music metadata extraction expert specializing in jazz. Return only valid JSON arrays. Use your full training knowledge to add comprehensive metadata."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=2000  # Increased for more detailed responses
        )

        response_content = response.choices[0].message.content

        # Strip markdown code blocks if present
        if response_content.startswith('```'):
            lines = response_content.split('\n')
            response_content = '\n'.join(lines[1:-1])  # Remove first and last line

        result = json.loads(response_content)
        return result if isinstance(result, list) else [result]

    except Exception as e:
        print(f"❌ Error processing video '{video_title}': {e}")
        return []

def main():
    conn = sqlite3.connect('../database/piano_jazz_videos.db')
    cursor = conn.cursor()

    # Clear existing songs table
    print("🗑️  Clearing existing songs table...")
    cursor.execute('DELETE FROM songs')
    conn.commit()

    # Get all videos
    cursor.execute('SELECT id, title, description, url FROM videos ORDER BY id')
    videos = cursor.fetchall()
    total = len(videos)

    print(f"\n🤖 Starting FULL LLM extraction for {total} videos...")
    print("=" * 60)

    total_songs = 0

    for idx, (video_id, title, description, url) in enumerate(videos, 1):
        print(f"\n[{idx}/{total}] Processing: {title[:60]}...")

        # Let LLM extract everything
        songs = extract_video_data(title, description or "", url)

        if songs:
            # Insert all extracted songs with full metadata
            for song_idx, song in enumerate(songs, 1):
                # Convert featured_artists list to JSON string
                featured_artists = song.get('featured_artists')
                if isinstance(featured_artists, list):
                    featured_artists = json.dumps(featured_artists)

                cursor.execute('''
                    INSERT INTO songs (
                        video_id, song_title, composer, performer,
                        original_artist, timestamp, composition_year,
                        style, era, additional_info,
                        part_number, total_parts,
                        album, record_label, recording_year,
                        featured_artists, context_notes,
                        video_title, video_url, video_description, published_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    video_id,
                    song.get('song_title', title),
                    song.get('composer'),
                    song.get('performer'),  # Will be null if not specified or if it's Étienne
                    song.get('original_artist'),
                    song.get('timestamp'),
                    song.get('composition_year'),
                    song.get('style'),
                    song.get('era'),
                    song.get('additional_info'),
                    song_idx,
                    len(songs),
                    song.get('album'),
                    song.get('record_label'),
                    song.get('recording_year'),
                    featured_artists,
                    song.get('context_notes'),
                    title,
                    url,
                    description,
                    None  # published_at - will need to get from videos table
                ))

            total_songs += len(songs)
            print(f"  ✓ Extracted {len(songs)} song(s)")
        else:
            print(f"  - No songs extracted")

        # Save every 10 videos
        if idx % 10 == 0:
            conn.commit()
            print(f"\n💾 Progress saved ({idx}/{total} videos, {total_songs} songs)...")

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print(f"✅ Complete!")
    print(f"📊 Videos processed: {total}")
    print(f"🎵 Total songs extracted: {total_songs}")

if __name__ == '__main__':
    main()