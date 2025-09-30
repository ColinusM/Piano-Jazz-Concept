import sqlite3
import re

conn = sqlite3.connect('piano_jazz_videos.db')
cursor = conn.cursor()

# Create songs table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS songs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id INTEGER,
        song_title TEXT,
        composer TEXT,
        timestamp TEXT,
        part_number INTEGER,
        total_parts INTEGER,
        FOREIGN KEY (video_id) REFERENCES videos(id)
    )
''')

# Clear existing data
cursor.execute('DELETE FROM songs')

# Get all videos
cursor.execute('SELECT id, title, description, url FROM videos')
videos = cursor.fetchall()

for vid_id, title, desc, url in videos:
    # Extract timestamps and following text
    # Pattern: timestamp (HH:MM or MM:SS) followed by text until next timestamp or newline
    timestamp_pattern = r'(\d{1,2}:\d{2})\s*([^\n]+?)(?=\n\d{1,2}:\d{2}|\n\n|$)'
    matches = re.findall(timestamp_pattern, desc, re.DOTALL)

    if len(matches) >= 3:  # Compilation video with multiple segments
        total_parts = len(matches)
        for idx, (timestamp, segment_title) in enumerate(matches, 1):
            # Clean up segment title
            segment_title = segment_title.strip()
            # Remove URLs
            segment_title = re.sub(r'https?://\S+', '', segment_title).strip()
            # Limit length
            if len(segment_title) > 100:
                segment_title = segment_title[:100] + '...'

            # Try to extract composer
            composer = ''
            composer_match = re.search(r'\(([^)]+)\)', segment_title)
            if composer_match:
                composer = composer_match.group(1)

            cursor.execute('''
                INSERT INTO songs (video_id, song_title, composer, timestamp, part_number, total_parts)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (vid_id, segment_title if segment_title else f"Part {idx}", composer, timestamp, idx, total_parts))
    else:
        # Single song video
        # Extract composer from title if present
        composer = ''
        clean_title = title
        composer_match = re.search(r'\(([^)]+)\)', title)
        if composer_match:
            composer = composer_match.group(1)
            clean_title = re.sub(r'\s*\([^)]+\)', '', title).strip()

        # Check for "Artist | Song" format
        if '|' in clean_title:
            parts = clean_title.split('|')
            clean_title = parts[0].strip()
            if not composer and len(parts) > 1:
                composer = parts[1].strip()

        cursor.execute('''
            INSERT INTO songs (video_id, song_title, composer, timestamp, part_number, total_parts)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (vid_id, clean_title, composer, '', 1, 1))

conn.commit()

# Count results
cursor.execute('SELECT COUNT(*) FROM songs')
total_songs = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(DISTINCT video_id) FROM songs WHERE total_parts > 1')
compilations = cursor.fetchone()[0]

print(f"✓ Created songs table")
print(f"✓ Total songs: {total_songs}")
print(f"✓ Compilation videos: {compilations}")
print(f"✓ Single-song videos: {len(videos) - compilations}")

conn.close()