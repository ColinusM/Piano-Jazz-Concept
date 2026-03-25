import json
import os
import re
import sqlite3
import html
import requests
from datetime import datetime
from flask import Blueprint, request, session, jsonify, current_app

from app.db import get_db

api_bp = Blueprint('api', __name__)


# --- Song CRUD ---

@api_bp.route('/api/update_song', methods=['POST'])
def update_song():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    song_id = data.get('id')
    field = data.get('field')
    value = data.get('value')

    allowed_fields = ['song_title', 'composer', 'performer', 'original_artist',
                     'composition_year', 'style', 'era', 'additional_info',
                     'album', 'record_label', 'recording_year', 'context_notes',
                     'analysis_depth']
    if field not in allowed_fields:
        return jsonify({'success': False, 'error': 'Invalid field'}), 400

    try:
        print(f"[UPDATE] Updating song {song_id}: {field} = '{value}'")
        db = get_db()
        cursor = db.cursor()
        cursor.execute(f'UPDATE songs SET {field} = ? WHERE id = ?', (value, song_id))
        rows_affected = cursor.rowcount
        db.commit()
        print(f"[UPDATE] Success! {rows_affected} row(s) updated")
        return jsonify({'success': True})
    except sqlite3.OperationalError as e:
        if 'locked' in str(e):
            return jsonify({'success': False, 'error': 'Database is locked. Please try again later.'}), 503
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/api/update_category', methods=['POST'])
def update_category():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    item_id = data.get('id')
    category = data.get('category')
    view = data.get('view', 'songs')

    if not item_id or not category:
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400

    try:
        db = get_db()
        cursor = db.cursor()
        if view == 'videos':
            cursor.execute('UPDATE videos SET category = ? WHERE id = ?', (category, item_id))
        else:
            cursor.execute('UPDATE songs SET category = ? WHERE id = ?', (category, item_id))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/api/delete_song', methods=['POST'])
def delete_song():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    song_id = data.get('song_id')
    if not song_id:
        return jsonify({'success': False, 'error': 'Missing song_id'}), 400

    try:
        db = get_db()
        db.execute('UPDATE songs SET deleted = 1 WHERE id = ?', (song_id,))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/api/restore_song', methods=['POST'])
def restore_song():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    song_id = data.get('song_id')
    if not song_id:
        return jsonify({'success': False, 'error': 'Missing song_id'}), 400

    try:
        db = get_db()
        db.execute('UPDATE songs SET deleted = 0 WHERE id = ?', (song_id,))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/api/create_song', methods=['POST'])
def create_song():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    video_id = data.get('video_id')
    song_title = data.get('song_title')

    if not video_id or not song_title:
        return jsonify({'success': False, 'error': 'Missing video_id or song_title'}), 400

    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            SELECT id, title, description, url, thumbnail_url, published_at
            FROM videos WHERE id = ?
        ''', (video_id,))
        video = cursor.fetchone()
        if not video:
            return jsonify({'success': False, 'error': 'Video not found'}), 404

        cursor.execute('''
            INSERT INTO songs (
                video_id, song_title, video_title, video_url,
                video_description, published_at, part_number, total_parts, deleted
            ) VALUES (?, ?, ?, ?, ?, ?, 1, 1, 0)
        ''', (video[0], song_title, video[1], video[3], video[2], video[5]))

        new_song_id = cursor.lastrowid
        db.commit()
        return jsonify({'success': True, 'song_id': new_song_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# --- LLM Extraction ---

@api_bp.route('/api/get_master_prompt', methods=['GET'])
def get_master_prompt():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    try:
        with open('config/prompt_template.txt', 'r') as f:
            prompt = f.read()
        return jsonify({'success': True, 'prompt': prompt})
    except FileNotFoundError:
        default_prompt = open('utils/llm_full_extract.py', 'r').read()
        start = default_prompt.find('prompt = f"""') + 13
        end = default_prompt.find('"""', start)
        prompt_text = default_prompt[start:end]
        return jsonify({'success': True, 'prompt': prompt_text})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/api/enrich_video', methods=['POST'])
def enrich_video():
    """Extract songs from a video using LLM."""
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    video_id = data.get('video_id')
    if not video_id:
        return jsonify({'success': False, 'error': 'Missing video_id'}), 400

    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT title, description, url FROM videos WHERE id = ?', (video_id,))
        video = cursor.fetchone()
        if not video:
            return jsonify({'success': False, 'error': 'Video not found'}), 404

        video_title, video_description, video_url = video

        print(f"[ENRICH] Extracting songs from: {video_title}")
        songs = _extract_video_data(video_title, video_description, video_url)

        cursor.execute('DELETE FROM songs WHERE video_id = ?', (video_id,))

        for song in songs:
            cursor.execute('''
                INSERT INTO songs (
                    video_id, song_title, composer, performer, original_artist,
                    album, record_label, recording_year, composition_year,
                    style, era, featured_artists, context_notes, timestamp,
                    part_number, total_parts, video_title, video_url,
                    video_description, published_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_id, song.get('song_title'), song.get('composer'),
                song.get('performer'), song.get('original_artist'),
                song.get('album'), song.get('record_label'),
                song.get('recording_year'), song.get('composition_year'),
                song.get('style'), song.get('era'),
                ', '.join(song.get('featured_artists', [])) if song.get('featured_artists') else None,
                song.get('context_notes'), song.get('timestamp'),
                song.get('part_number', 1), song.get('total_parts', 1),
                video_title, video_url, video_description, None
            ))

        db.commit()
        print(f"[ENRICH] Extracted {len(songs)} song(s)")
        return jsonify({'success': True, 'songs_count': len(songs)})
    except Exception as e:
        print(f"[ENRICH] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# --- Changelog / Notifications ---

@api_bp.route('/api/get_changelog', methods=['GET'])
def get_changelog():
    try:
        changelog_path = 'CHANGELOG.md'
        if not os.path.exists(changelog_path):
            return jsonify({'success': True, 'updates': [], 'count': 0})

        last_seen = session.get('changelog_last_seen', 0)
        updates = []
        current_date = None
        current_section = None

        with open(changelog_path, 'r', encoding='utf-8') as f:
            for line in f:
                line_stripped = line.strip()
                if line_stripped.startswith('## ') and len(line_stripped) > 3:
                    date_str = line_stripped[3:].strip()
                    if date_str[0].isdigit():
                        try:
                            entry_time = datetime.strptime(date_str, '%Y-%m-%d').replace(hour=23, minute=59).timestamp()
                            current_date = {
                                'date': date_str,
                                'timestamp': entry_time,
                                'sections': {},
                                'is_new': entry_time > last_seen
                            }
                            updates.append(current_date)
                            current_section = None
                        except:
                            pass
                elif line_stripped.startswith('### ') and current_date:
                    section_name = line_stripped[4:].strip()
                    current_section = section_name
                    current_date['sections'][section_name] = []
                elif line_stripped.startswith('- ') and current_date:
                    change = line_stripped[2:].strip()
                    if not current_section:
                        if 'Général' not in current_date['sections']:
                            current_date['sections']['Général'] = []
                        current_date['sections']['Général'].append(change)
                    else:
                        current_date['sections'][current_section].append(change)

        new_count = sum(1 for u in updates if u['is_new'])
        return jsonify({'success': True, 'updates': updates, 'count': new_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/api/mark_changelog_seen', methods=['POST'])
def mark_changelog_seen():
    try:
        session['changelog_last_seen'] = datetime.now().timestamp()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# --- Auto-update pipeline ---

@api_bp.route('/api/auto_update', methods=['POST'])
def auto_update():
    """Scrape YouTube for latest videos, extract songs from new ones."""
    try:
        youtube_api_key = current_app.config.get('YOUTUBE_API_KEY')
        openai_api_key = current_app.config.get('OPENAI_API_KEY')

        if not youtube_api_key or not openai_api_key:
            return jsonify({'success': False, 'error': 'API keys not configured'}), 500

        db = get_db()
        cursor = db.cursor()

        channel_handle = 'Pianojazzconcept'
        search_resp = requests.get('https://www.googleapis.com/youtube/v3/search', params={
            'key': youtube_api_key, 'q': channel_handle, 'type': 'channel', 'part': 'snippet'
        }).json()

        if 'items' not in search_resp or len(search_resp['items']) == 0:
            return jsonify({'success': False, 'error': 'Channel not found'}), 404

        channel_id = search_resp['items'][0]['id']['channelId']

        cursor.execute('SELECT video_id FROM videos')
        existing_video_ids = set(row[0] for row in cursor.fetchall())

        new_videos = []
        videos_to_extract = []

        response = requests.get('https://www.googleapis.com/youtube/v3/search', params={
            'key': youtube_api_key, 'channelId': channel_id,
            'part': 'snippet', 'type': 'video', 'maxResults': 50, 'order': 'date'
        }).json()

        video_ids = [item['id']['videoId'] for item in response.get('items', [])]

        if video_ids:
            details_response = requests.get('https://www.googleapis.com/youtube/v3/videos', params={
                'key': youtube_api_key, 'id': ','.join(video_ids), 'part': 'snippet'
            }).json()

            for item in details_response.get('items', []):
                video_id = item['id']
                title = html.unescape(item['snippet']['title'])
                description = html.unescape(item['snippet']['description'])
                url = f"https://youtube.com/watch?v={video_id}"
                published_at = item['snippet']['publishedAt']

                thumbnails = item['snippet']['thumbnails']
                thumbnail_url = (thumbnails.get('maxres') or thumbnails.get('high') or
                               thumbnails.get('medium') or thumbnails.get('default'))['url']

                is_new = video_id not in existing_video_ids

                cursor.execute('''
                    INSERT OR REPLACE INTO videos (video_id, title, description, url, published_at, thumbnail_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (video_id, title, description, url, published_at, thumbnail_url))

                db_video_id = cursor.lastrowid

                if is_new:
                    vid_data = {'id': db_video_id, 'video_id': video_id,
                               'title': title, 'description': description, 'url': url}
                    new_videos.append(vid_data)
                    videos_to_extract.append(vid_data)

        db.commit()

        new_songs_count = 0
        if videos_to_extract:
            for video in videos_to_extract:
                songs = _extract_video_data(video['title'], video['description'] or '', video['url'])
                if songs:
                    for song_idx, song in enumerate(songs, 1):
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
                            video['id'], song.get('song_title', video['title']),
                            song.get('composer'), song.get('performer'),
                            song.get('original_artist'), song.get('timestamp'),
                            song.get('composition_year'), song.get('style'),
                            song.get('era'), song.get('additional_info'),
                            song_idx, len(songs),
                            song.get('album'), song.get('record_label'),
                            song.get('recording_year'), featured_artists,
                            song.get('context_notes'), video['title'],
                            video['url'], video['description'], None
                        ))
                    new_songs_count += len(songs)

        db.commit()

        return jsonify({
            'success': True,
            'new_videos': len(new_videos),
            'new_songs': new_songs_count,
            'message': f'Found {len(new_videos)} new video(s), extracted {new_songs_count} song(s)'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# --- Internal helpers ---

def _get_openai_client():
    """Lazy-init OpenAI client."""
    api_key = current_app.config.get('OPENAI_API_KEY')
    if not api_key:
        return None
    api_key = api_key.strip().replace('\n', '').replace('\r', '').replace(' ', '')
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def _extract_video_data(video_title, video_description, video_url, prompt_guidance=''):
    """Extract song data from a video using OpenAI LLM."""
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

IMPORTANT - WHEN TO EXTRACT:

✓ ALWAYS extract when title contains "Song/Piece Title (Composer)" or "Title | Artist":
  - The title itself IS the song, even if description is empty

✓ ALWAYS check description for specific songs, even in theory videos

✗ ONLY skip extraction when:
  - Theory/technique topic AND no specific songs mentioned anywhere
  - Generic discussion with no named compositions in title OR description

YOUR TASK:
Extract ALL songs/pieces analyzed in this video with MAXIMUM metadata.

Return JSON array:
- If songs found: return array with song objects
- If NO songs mentioned/analyzed: return empty array []

Example response:
[
  {{
    "song_title": "song name",
    "composer": "who wrote it",
    "performer": "whose recording is analyzed (NEVER Étienne)",
    "original_artist": "if it's a cover",
    "album": "album name if known",
    "record_label": "label if known",
    "recording_year": null,
    "composition_year": null,
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

    if prompt_guidance:
        prompt += f"\n\nADDITIONAL GUIDANCE:\n{prompt_guidance}"

    try:
        client = _get_openai_client()
        if not client:
            return []

        print(f"[EXTRACT] Extracting songs from: {video_title}")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a music metadata extraction expert specializing in jazz. Return only valid JSON arrays."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=2000,
            timeout=60.0
        )

        response_content = response.choices[0].message.content
        if response_content.startswith('```'):
            lines = response_content.split('\n')
            response_content = '\n'.join(lines[1:-1])

        result = json.loads(response_content)
        songs = result if isinstance(result, list) else [result]
        print(f"[EXTRACT] Extracted {len(songs)} song(s)")
        return songs
    except Exception as e:
        import traceback
        import sys
        print(f"[EXTRACT] Error ({type(e).__name__}): {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return []
