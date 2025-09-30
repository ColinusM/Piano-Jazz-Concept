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
    Give LLM the raw video data and let it extract EVERYTHING.
    """

    prompt = f"""Analyze this Piano Jazz Concept YouTube video and extract ALL songs and metadata.

VIDEO TITLE: {video_title}
VIDEO URL: {video_url}
FULL DESCRIPTION:
{video_description}

Extract EVERYTHING from this video:
- All songs mentioned (with timestamps if present)
- Composer for each song
- Performer/pianist
- Original artists (if covers)
- Years, styles, eras
- Any other musical metadata

Return JSON array of songs. If single song, return array with 1 item:
[
  {{
    "song_title": "song name",
    "composer": "who wrote it",
    "performer": "who plays in this video",
    "original_artist": "if it's a cover",
    "timestamp": "MM:SS or null",
    "composition_year": year or null,
    "style": "genre",
    "era": "decade/era",
    "additional_info": "any other info"
  }}
]

Use both the text AND your training knowledge. Be comprehensive!"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a music metadata extraction expert. Return only valid JSON arrays."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=1000
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

    # Get single test video (Jacob Collier)
    cursor.execute('SELECT id, title, description, url FROM videos WHERE id = 392')
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
            # Insert all extracted songs
            for song_idx, song in enumerate(songs, 1):
                cursor.execute('''
                    INSERT INTO songs (
                        video_id, song_title, composer, performer,
                        original_artist, timestamp, composition_year,
                        style, era, additional_info,
                        part_number, total_parts
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    video_id,
                    song.get('song_title', title),
                    song.get('composer'),
                    song.get('performer'),
                    song.get('original_artist'),
                    song.get('timestamp'),
                    song.get('composition_year'),
                    song.get('style'),
                    song.get('era'),
                    song.get('additional_info'),
                    song_idx,
                    len(songs)
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