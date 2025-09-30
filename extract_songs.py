"""
Reads all video descriptions from the database and extracts individual songs.
Outputs a formatted list of all songs found.
"""
import sqlite3

conn = sqlite3.connect('piano_jazz_videos.db')
cursor = conn.cursor()

# Get all videos with descriptions
cursor.execute('SELECT id, title, description, url FROM videos ORDER BY id')
videos = cursor.fetchall()

print("="*80)
print("EXTRACTING SONGS FROM VIDEO DESCRIPTIONS")
print("="*80)
print()

all_songs = []

for video_id, title, description, url in videos:
    # Analysis logic - I (Claude) will analyze each description
    # For now, just collect data for manual analysis
    all_songs.append({
        'video_id': video_id,
        'title': title,
        'description': description,
        'url': url
    })

# Output for analysis
print(f"Total videos: {len(videos)}")
print()
print("Outputting all titles and descriptions for analysis...")
print()

# Save to file for Claude to analyze
with open('songs_to_analyze.txt', 'w') as f:
    for video in all_songs:
        f.write(f"VIDEO #{video['video_id']}\n")
        f.write(f"Title: {video['title']}\n")
        f.write(f"URL: {video['url']}\n")
        f.write(f"Description: {video['description']}\n")
        f.write("-"*80 + "\n\n")

print(f"✓ Exported {len(videos)} videos to 'songs_to_analyze.txt'")
print()
print("Next step: Claude will analyze this file and extract individual songs")

conn.close()