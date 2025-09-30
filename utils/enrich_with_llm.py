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

    prompt = f"""Analyze this Piano Jazz Concept video data and extract ALL structured metadata you can find.

Video Title: {video_title}
Video Description: {video_description}
Song Title: {song_title}
Current Composer: {current_composer or "Unknown"}

Extract EVERYTHING relevant from TWO SOURCES:
1. PRIMARY: Information found in the text above
2. SECONDARY: Your knowledge about the song/artist (if you're confident)

Fields to extract:
- Performer/pianist name (who plays it in THIS video)
- Composer/songwriter names (who wrote the original song)
- Original artist (if it's a cover, e.g., Johnny Hallyday)
- Featured artists (feat., avec, etc.)
- Composition year or era (from text OR your knowledge if famous song)
- Other musicians (bass, drums, etc.)
- Album or recording info
- Musical style/genre
- Era/decade of the original song
- Any other relevant musical metadata

Return JSON with ALL fields. Use your knowledge to fill in gaps when you're confident:
{{
    "performer": "name or null",
    "composer": "name or null",
    "songwriters": "names or null",
    "original_artist": "name or null",
    "featured_artists": ["list or null"],
    "composition_year": year_integer or null,
    "other_musicians": {{"instrument": "name"}} or null,
    "album": "name or null",
    "style": "genre/style or null",
    "era": "decade or era or null",
    "additional_info": "any other relevant info or null",
    "data_source": "text_only|text_and_knowledge|knowledge_only"
}}

Be comprehensive - use both the text AND your training knowledge!"""

    try:
        # DEBUG: Print the exact prompt being sent
        print("\n" + "="*80)
        print("🔍 PROMPT SENT TO LLM:")
        print("="*80)
        print(prompt)
        print("="*80)

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

        # DEBUG: Print the exact response received
        print("\n🤖 LLM RESPONSE:")
        print("="*80)
        print(response_content)
        print("="*80)

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

    # Get specific songs for debug testing
    cursor.execute('''
        SELECT
            s.id,
            s.song_title,
            s.composer,
            v.title as video_title,
            v.description
        FROM songs s
        JOIN videos v ON s.video_id = v.id
        WHERE v.title LIKE '%Que je t''aime%'
        LIMIT 1
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