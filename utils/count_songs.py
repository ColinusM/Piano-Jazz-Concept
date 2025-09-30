import sqlite3
import re

conn = sqlite3.connect('../database/piano_jazz_videos.db')
cursor = conn.cursor()
cursor.execute('SELECT id, title, description FROM videos')
videos = cursor.fetchall()

total_songs = 0
compilations = []

for vid_id, title, desc in videos:
    # Count timestamps in description (indicates multiple segments/songs)
    timestamps = re.findall(r'\d{1,2}:\d{2}', desc)

    if len(timestamps) >= 3:  # At least 3 timestamps = compilation
        compilations.append({
            'id': vid_id,
            'title': title,
            'segments': len(timestamps)
        })
        total_songs += len(timestamps)
    else:
        total_songs += 1  # Single song video

print(f"Total videos: {len(videos)}")
print(f"Compilation videos (3+ segments): {len(compilations)}")
print(f"Estimated total songs/segments: {total_songs}")
print(f"\nCompilations found:")
for comp in compilations[:10]:  # Show first 10
    print(f"  [{comp['id']}] {comp['title']} - {comp['segments']} segments")

conn.close()