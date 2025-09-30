import sqlite3
import re

def extract_artist_from_title(title):
    """Extract artist/composer names from title"""
    # Patterns: "Artist | Song", "Song (Artist)", "Artist : Song"
    patterns = [
        r'([^|]+)\s*\|\s*',  # Artist | Song
        r'\(([^)]+)\)',      # (Artist)
        r'([^:]+)\s*:\s*',   # Artist : Song
        r'feat\.\s+([^&]+)', # feat. Artist
    ]

    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            return match.group(1).strip()
    return ''

def is_likely_song_name(text):
    """Check if text looks like a song name"""
    text = text.strip()
    # Must be reasonable length
    if len(text) < 3 or len(text) > 100:
        return False
    # Should not be just a URL or time
    if re.match(r'^https?://', text) or re.match(r'^\d{1,2}:\d{2}', text):
        return False
    # Should not be generic text
    generic = ['intro', 'outro', 'conclusion', 'bases', 'concert', 'code promo']
    if text.lower() in generic:
        return False
    return True

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
    # Extract artist/composer from title first
    main_artist = extract_artist_from_title(title)

    # Extract timestamps and following text from BOTH title and description
    # Pattern: timestamp (HH:MM or MM:SS) followed by text until next timestamp or newline
    timestamp_pattern = r'(\d{1,2}:\d{2})\s*([^\n]+?)(?=\n\d{1,2}:\d{2}|\n\n|$)'
    matches = re.findall(timestamp_pattern, desc, re.DOTALL)

    # Filter matches to only include likely song names
    valid_matches = []
    for timestamp, segment_title in matches:
        segment_title = segment_title.strip()
        # Remove URLs
        segment_title = re.sub(r'https?://\S+', '', segment_title).strip()

        if is_likely_song_name(segment_title):
            valid_matches.append((timestamp, segment_title))

    if len(valid_matches) >= 3:  # Compilation video with multiple segments
        total_parts = len(valid_matches)
        for idx, (timestamp, segment_title) in enumerate(valid_matches, 1):
            # Limit length
            if len(segment_title) > 100:
                segment_title = segment_title[:100] + '...'

            # Try to extract composer from segment or use main artist
            composer = ''
            composer_match = re.search(r'\(([^)]+)\)', segment_title)
            if composer_match:
                composer = composer_match.group(1)
                segment_title = re.sub(r'\s*\([^)]+\)', '', segment_title).strip()
            elif main_artist:
                composer = main_artist

            cursor.execute('''
                INSERT INTO songs (video_id, song_title, composer, timestamp, part_number, total_parts)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (vid_id, segment_title, composer, timestamp, idx, total_parts))
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

        # Use main_artist if no composer found
        if not composer:
            composer = main_artist

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