"""
LLM-based enrichment of song metadata.
Extracts performer names, composition years, songwriters, and improves composer attribution.
"""
import sqlite3
import json
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(
    api_key="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"
)

def enrich_song_metadata(video_title, video_description, song_title, current_composer):
    """
    Use LLM to extract additional metadata from video content.
    Returns dict with: performer, composition_year, songwriters, improved_composer
    """

    prompt = f"""Analyze this Piano Jazz Concept video and extract metadata for THIS SPECIFIC SONG.

Video Title: {video_title}
Video Description (with timestamps): {video_description}
Song Title: {song_title}
Current Composer: {current_composer or "Unknown"}

IMPORTANT CONTEXT CLUES:
- If video title has "feat." or mentions multiple artists (e.g., "feat. Jacob Collier et Mark Priore"), these are FEATURED artists being ANALYZED/COMPARED
- When multiple songs are timestamped, each song may have a DIFFERENT composer from the featured list
- Look at the song title and match it to the appropriate composer
- The PERFORMER is who plays piano in this video (usually Étienne Guéreau or mentioned in description)
- The COMPOSER is who originally wrote THIS specific song

SMART MATCHING RULES:
1. If the video compares works by multiple composers, match the song title to the correct composer
2. Example: Video "feat. Collier et Priore" with songs "Orphée" and "Hajanga" - determine which composer wrote which song
3. Use your knowledge of who wrote what song when available
4. Don't just copy all names to all songs - BE SPECIFIC to THIS song

Extract from TWO SOURCES:
1. Text above (primary)
2. Your knowledge (secondary - use for composition dates, correct attribution, etc.)

Return JSON with ACCURATE, SONG-SPECIFIC data:
{{
    "performer": "who plays piano in THIS video",
    "composer": "who wrote THIS SPECIFIC song (not all featured artists)",
    "songwriters": "who wrote THIS song",
    "original_artist": "original artist if it's a cover",
    "featured_artists": ["artists being compared/analyzed in video"],
    "composition_year": year_integer or null,
    "other_musicians": {{"instrument": "name"}} or null,
    "album": "name or null",
    "style": "genre/style",
    "era": "decade or era",
    "additional_info": "relevant info",
    "data_source": "text_only|text_and_knowledge|knowledge_only"
}}

Be SMART and SPECIFIC - match the song to its actual composer!"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a metadata extraction assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=500
        )

        response_content = response.choices[0].message.content
        result = json.loads(response_content)
        return result

    except Exception as e:
        print(f"Error processing '{song_title}': {e}")
        return {
            "performer": None,
            "composition_year": None,
            "songwriters": None,
            "improved_composer": None
        }

def main():
    # Connect to database
    conn = sqlite3.connect('../database/piano_jazz_videos.db')
    cursor = conn.cursor()

    # Add new columns if they don't exist
    new_columns = [
        ('performer', 'TEXT'),
        ('composition_year', 'INTEGER'),
        ('songwriters', 'TEXT'),
        ('original_artist', 'TEXT'),
        ('featured_artists', 'TEXT'),
        ('other_musicians', 'TEXT'),
        ('style', 'TEXT'),
        ('era', 'TEXT'),
        ('data_source', 'TEXT'),
        ('additional_info', 'TEXT')
    ]

    for col_name, col_type in new_columns:
        try:
            cursor.execute(f'ALTER TABLE songs ADD COLUMN {col_name} {col_type}')
            print(f"✓ Added column: {col_name}")
        except sqlite3.OperationalError:
            pass  # Column already exists

    print("ℹ Database schema updated")

    # Get songs from Jacob Collier video
    cursor.execute('''
        SELECT
            s.id,
            s.song_title,
            s.composer,
            v.title as video_title,
            v.description
        FROM songs s
        JOIN videos v ON s.video_id = v.id
        WHERE v.id = 392
        ORDER BY s.id
    ''')

    songs = cursor.fetchall()
    total = len(songs)

    print(f"\n🤖 Starting LLM enrichment for {total} songs...")
    print("=" * 60)

    enriched_count = 0

    for idx, (song_id, song_title, composer, video_title, video_desc) in enumerate(songs, 1):
        print(f"\n[{idx}/{total}] Processing: {song_title[:50]}...")

        # Get enriched metadata from LLM
        metadata = enrich_song_metadata(video_title, video_desc or "", song_title, composer)

        # Convert complex types to JSON strings for storage
        import json
        songwriters_str = json.dumps(metadata.get('songwriters')) if metadata.get('songwriters') else None
        featured_str = json.dumps(metadata.get('featured_artists')) if metadata.get('featured_artists') else None
        musicians_str = json.dumps(metadata.get('other_musicians')) if metadata.get('other_musicians') else None

        # Update composer if found
        updated_composer = metadata.get('composer') or composer

        # Update database
        cursor.execute('''
            UPDATE songs
            SET performer = ?,
                composition_year = ?,
                songwriters = ?,
                original_artist = ?,
                featured_artists = ?,
                other_musicians = ?,
                style = ?,
                era = ?,
                data_source = ?,
                additional_info = ?,
                composer = ?
            WHERE id = ?
        ''', (
            metadata.get('performer'),
            metadata.get('composition_year'),
            songwriters_str,
            metadata.get('original_artist'),
            featured_str,
            musicians_str,
            metadata.get('style'),
            metadata.get('era'),
            metadata.get('data_source'),
            metadata.get('additional_info'),
            updated_composer,
            song_id
        ))

        # Show what was found
        found = []
        if metadata.get('performer'):
            found.append(f"Performer: {metadata['performer']}")
        if metadata.get('original_artist'):
            found.append(f"Original: {metadata['original_artist']}")
        if metadata.get('songwriters'):
            found.append(f"Songwriters: {metadata['songwriters']}")
        if metadata.get('composition_year'):
            found.append(f"Year: {metadata['composition_year']}")
        if metadata.get('other_musicians'):
            found.append(f"Musicians: {len(metadata['other_musicians'])} found")
        if metadata.get('style'):
            found.append(f"Style: {metadata['style']}")

        if found:
            print(f"  ✓ Found: {', '.join(found)}")
            enriched_count += 1
        else:
            print(f"  - No additional metadata found")

        # Commit every 10 songs to avoid data loss
        if idx % 10 == 0:
            conn.commit()
            print(f"\n💾 Progress saved ({idx}/{total})...")

    # Final commit
    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print(f"✅ Enrichment complete!")
    print(f"📊 Total songs: {total}")
    print(f"🎵 Enriched with metadata: {enriched_count}")
    print(f"📈 Success rate: {enriched_count/total*100:.1f}%")

if __name__ == '__main__':
    main()