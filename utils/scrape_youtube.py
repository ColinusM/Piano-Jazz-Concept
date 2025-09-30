import requests
import sqlite3
import json
import html

API_KEY = 'AIzaSyBM3GSMWBG78DNAj5xVFkvKIZ687HVf3lM'
CHANNEL_HANDLE = 'Pianojazzconcept'

# Create database
conn = sqlite3.connect('../database/piano_jazz_videos.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT UNIQUE,
        title TEXT,
        description TEXT,
        url TEXT,
        published_at TEXT
    )
''')

# Get channel ID
search = requests.get('https://www.googleapis.com/youtube/v3/search', params={
    'key': API_KEY,
    'q': CHANNEL_HANDLE,
    'type': 'channel',
    'part': 'snippet'
}).json()

channel_id = search['items'][0]['id']['channelId']
print(f"Channel ID: {channel_id}")

# Get all videos
next_page = None
video_count = 0

while True:
    params = {
        'key': API_KEY,
        'channelId': channel_id,
        'part': 'snippet',
        'type': 'video',
        'maxResults': 50,
        'order': 'date'
    }
    if next_page:
        params['pageToken'] = next_page

    response = requests.get('https://www.googleapis.com/youtube/v3/search', params=params).json()

    # Collect video IDs
    video_ids = [item['id']['videoId'] for item in response['items']]

    # Fetch full details including complete descriptions
    if video_ids:
        details_response = requests.get('https://www.googleapis.com/youtube/v3/videos', params={
            'key': API_KEY,
            'id': ','.join(video_ids),
            'part': 'snippet'
        }).json()

        for item in details_response.get('items', []):
            video_id = item['id']
            title = html.unescape(item['snippet']['title'])
            description = html.unescape(item['snippet']['description'])
            url = f"https://youtube.com/watch?v={video_id}"
            published_at = item['snippet']['publishedAt']

            cursor.execute('''
                INSERT OR REPLACE INTO videos (video_id, title, description, url, published_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (video_id, title, description, url, published_at))

            video_count += 1
            print(f"Added: {title}")

    conn.commit()

    next_page = response.get('nextPageToken')
    if not next_page:
        break

print(f"\nTotal videos scraped: {video_count}")
conn.close()