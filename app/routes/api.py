import json
import os
import re
import sqlite3
import html
import time
import requests
from datetime import datetime
from flask import Blueprint, request, session, jsonify, current_app, redirect

import google_auth_oauthlib.flow
import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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


# --- YouTube Description Updater ---

YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

# --- Production config (Étienne's channel) ---
# OLD_DOMAIN_PATTERN = r'https?://piano-jazz-concept\.onrender\.com[^\s]*'
# NEW_URL = 'https://pianojazzconcept.pythonanywhere.com/?view=index'

# --- Test config (Colin's channel) ---
OLD_CONTENT_MARKER = 'I need money'
NEW_CONTENT_MARKER = 'Get immediate access'


def _needs_update(description):
    """Check if a description contains content that needs updating."""
    return (OLD_CONTENT_MARKER.lower() in description.lower() or
            'all other and all future ones' in description.lower())


def _is_already_updated(description):
    """Check if a description has already been updated."""
    return NEW_CONTENT_MARKER.lower() in description.lower()


def _transform_description(description):
    """Apply all transformations to a description.

    1. Remove date + 'I need money' pitch (keep Patreon link)
    2. Replace file text with new wording
    3. Deduplicate email lines
    """
    # 1. Remove date + pitch: "11 October 2024 "Hello, I need money...more info there"
    #    Keep everything from the Patreon link onwards
    description = re.sub(
        r'\d{1,2}\s+\w+\s+\d{4}\s*"?Hello.*?more info there\s*',
        '',
        description,
        flags=re.IGNORECASE | re.DOTALL
    )

    # 2. Replace file text (with optional closing quote)
    description = re.sub(
        r'You will get this file and all other and all future ones"?',
        'Get immediate access to this file and all previous ones for just $3',
        description,
        flags=re.IGNORECASE
    )

    # 3. Deduplicate email/queries lines
    email_pattern = r'(?:email|queries)\s*:\s*colin\.mignot1@gmail\.com'
    matches = list(re.finditer(email_pattern, description, re.IGNORECASE))
    if len(matches) > 1:
        for match in reversed(matches[1:]):
            start = match.start()
            end = match.end()
            # Remove surrounding newlines too
            while start > 0 and description[start - 1] == '\n':
                start -= 1
            while end < len(description) and description[end:end + 1] == '\n':
                end += 1
            description = description[:start] + description[end:]

    # Clean up extra blank lines
    description = re.sub(r'\n{3,}', '\n\n', description)
    return description.strip()


def _get_youtube_redirect_uri():
    """Build OAuth redirect URI, forcing HTTPS on PythonAnywhere."""
    redirect_uri = request.host_url.rstrip('/') + '/oauth2callback'
    if 'pythonanywhere.com' in redirect_uri:
        redirect_uri = redirect_uri.replace('http://', 'https://')
    return redirect_uri


def _save_youtube_credentials(credentials):
    """Persist OAuth credentials to file (session is too small)."""
    creds_data = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': list(credentials.scopes or []),
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    creds_path = os.path.join(DATA_DIR, 'youtube_oauth_creds.json')
    with open(creds_path, 'w') as f:
        json.dump(creds_data, f, indent=2)


def _load_youtube_credentials():
    """Load OAuth credentials from file."""
    creds_path = os.path.join(DATA_DIR, 'youtube_oauth_creds.json')
    if not os.path.exists(creds_path):
        return None
    with open(creds_path) as f:
        creds_data = json.load(f)
    return google.oauth2.credentials.Credentials(
        token=creds_data['token'],
        refresh_token=creds_data.get('refresh_token'),
        token_uri=creds_data['token_uri'],
        client_id=creds_data['client_id'],
        client_secret=creds_data['client_secret'],
        scopes=creds_data.get('scopes'),
    )


@api_bp.route('/api/youtube-oauth-start')
def youtube_oauth_start():
    """Start OAuth2 flow — redirect admin to Google consent screen."""
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    if current_app.debug:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    client_secret_path = current_app.config.get('YOUTUBE_CLIENT_SECRET_PATH')
    if not client_secret_path or not os.path.exists(client_secret_path):
        return jsonify({'success': False, 'error': 'Configuration OAuth manquante'}), 500

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        client_secret_path,
        scopes=YOUTUBE_SCOPES
    )
    flow.redirect_uri = _get_youtube_redirect_uri()

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    session['youtube_oauth_state'] = state
    # Save PKCE code_verifier — needed to exchange the code in the callback
    session['youtube_code_verifier'] = flow.code_verifier
    return redirect(authorization_url)


@api_bp.route('/oauth2callback')
def oauth2callback():
    """Handle Google OAuth2 callback — exchange code for credentials."""
    if not session.get('admin'):
        return redirect('/')

    state = session.get('youtube_oauth_state')
    if not state:
        return redirect('/?youtube_update=error')

    if current_app.debug:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    client_secret_path = current_app.config.get('YOUTUBE_CLIENT_SECRET_PATH')
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        client_secret_path,
        scopes=YOUTUBE_SCOPES,
        state=state
    )
    flow.redirect_uri = _get_youtube_redirect_uri()
    # Restore PKCE code_verifier from session
    flow.code_verifier = session.get('youtube_code_verifier')

    # Fix for PythonAnywhere reverse proxy: force HTTPS in the callback URL
    authorization_response = request.url
    if 'pythonanywhere.com' in authorization_response:
        authorization_response = authorization_response.replace('http://', 'https://')

    try:
        flow.fetch_token(authorization_response=authorization_response)
    except Exception as e:
        print(f"[YOUTUBE] OAuth token exchange error: {e}")
        return redirect('/?youtube_update=error')

    _save_youtube_credentials(flow.credentials)
    session.pop('youtube_oauth_state', None)

    return redirect('/?youtube_update=analyze')


@api_bp.route('/api/youtube-analyze', methods=['POST'])
def youtube_analyze():
    """Scan all channel videos and categorize by link status."""
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    credentials = _load_youtube_credentials()
    if not credentials:
        return jsonify({'success': False, 'error': 'not_authenticated'}), 401

    try:
        youtube = build('youtube', 'v3', credentials=credentials)

        # Get the authenticated user's channel
        channels_response = youtube.channels().list(
            part='contentDetails',
            mine=True
        ).execute()

        if not channels_response.get('items'):
            return jsonify({'success': False, 'error': 'Aucune chaîne YouTube trouvée pour ce compte'}), 404

        uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # Fetch ALL video IDs from the uploads playlist (paginated)
        all_video_ids = []
        next_page_token = None
        while True:
            playlist_response = youtube.playlistItems().list(
                playlistId=uploads_playlist_id,
                part='snippet',
                maxResults=50,
                pageToken=next_page_token
            ).execute()

            for item in playlist_response.get('items', []):
                all_video_ids.append(item['snippet']['resourceId']['videoId'])

            next_page_token = playlist_response.get('nextPageToken')
            if not next_page_token:
                break

        # Batch-fetch video snippets + status (50 at a time) and categorize
        to_update = []  # Videos with old content to replace
        to_add = []     # Videos with no link at all — will add the new link
        already_correct = 0
        skipped_private = 0

        for i in range(0, len(all_video_ids), 50):
            batch_ids = all_video_ids[i:i + 50]
            videos_response = youtube.videos().list(
                part='snippet,status',
                id=','.join(batch_ids)
            ).execute()

            for video in videos_response.get('items', []):
                # Skip private videos
                privacy = video.get('status', {}).get('privacyStatus', 'public')
                if privacy == 'private':
                    skipped_private += 1
                    continue

                video_id = video['id']
                title = video['snippet'].get('title', '')
                description = video['snippet'].get('description', '')

                needs_update = _needs_update(description)
                already_done = _is_already_updated(description)

                if needs_update:
                    to_update.append({'video_id': video_id, 'title': title, 'action': 'replace'})
                elif already_done:
                    already_correct += 1
                else:
                    to_add.append({'video_id': video_id, 'title': title, 'action': 'add'})

        # Combine both lists: replacements first, then additions
        all_actions = to_update + to_add

        # Save analysis to file (too large for cookie-based session)
        analysis = {
            'to_update': all_actions,
            'already_correct': already_correct,
            'total': len(all_video_ids) - skipped_private,
            'analyzed_at': datetime.now().isoformat()
        }
        os.makedirs(DATA_DIR, exist_ok=True)
        analysis_path = os.path.join(DATA_DIR, 'youtube_analysis.json')
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)

        # Refresh saved credentials (token may have been auto-refreshed)
        _save_youtube_credentials(credentials)

        # Preview: first 3 video titles for the test button
        test_preview = [v['title'] for v in all_actions[:3]]

        return jsonify({
            'success': True,
            'to_replace': len(to_update),
            'to_add': len(to_add),
            'already_correct': already_correct,
            'skipped_private': skipped_private,
            'total': len(all_video_ids) - skipped_private,
            'test_preview': test_preview
        })

    except HttpError as e:
        print(f"[YOUTUBE] API error during analysis: {e}")
        return jsonify({'success': False, 'error': f'Erreur YouTube: {e.resp.status}'}), 500
    except Exception as e:
        print(f"[YOUTUBE] Error during analysis: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/api/youtube-apply', methods=['POST'])
def youtube_apply():
    """Apply description updates to YouTube videos. HIGH STAKES — handle with care."""
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    mode = data.get('mode', 'test')  # 'test' = first 3, 'all' = remaining (max 190)

    credentials = _load_youtube_credentials()
    if not credentials:
        return jsonify({'success': False, 'error': 'not_authenticated'}), 401

    # Load analysis from file
    analysis_path = os.path.join(DATA_DIR, 'youtube_analysis.json')
    if not os.path.exists(analysis_path):
        return jsonify({'success': False, 'error': "Analyse non trouvée. Relancez l'analyse."}), 400

    with open(analysis_path, 'r', encoding='utf-8') as f:
        analysis = json.load(f)

    to_update = analysis.get('to_update', [])
    if not to_update:
        return jsonify({'success': True, 'updated': [], 'failed': [], 'remaining': 0, 'quota_exceeded': False})

    # Determine batch
    batch = to_update[:3] if mode == 'test' else to_update[:190]

    updated = []
    failed = []
    quota_exceeded = False
    successfully_processed_ids = set()

    try:
        youtube = build('youtube', 'v3', credentials=credentials)

        # SAFETY STEP 1: Backup all current descriptions before any modification
        backup_data = {}
        for i in range(0, len(batch), 50):
            batch_ids = [v['video_id'] for v in batch[i:i + 50]]
            response = youtube.videos().list(
                part='snippet',
                id=','.join(batch_ids)
            ).execute()
            for video in response.get('items', []):
                backup_data[video['id']] = {
                    'title': video['snippet'].get('title', ''),
                    'description': video['snippet'].get('description', ''),
                    'categoryId': video['snippet'].get('categoryId', ''),
                    'tags': video['snippet'].get('tags', []),
                }

        os.makedirs(DATA_DIR, exist_ok=True)
        backup_path = os.path.join(DATA_DIR, f'youtube_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        print(f"[YOUTUBE] Backup saved: {backup_path} ({len(backup_data)} videos)")

        # SAFETY STEP 2: Update one by one, re-reading each video fresh
        for video_info in batch:
            vid = video_info['video_id']

            try:
                # RE-READ current snippet (catches manual edits since analysis)
                response = youtube.videos().list(
                    part='snippet',
                    id=vid
                ).execute()

                if not response.get('items'):
                    failed.append({'video_id': vid, 'title': video_info['title'], 'error': 'Vidéo introuvable'})
                    successfully_processed_ids.add(vid)  # Remove from queue
                    continue

                snippet = response['items'][0]['snippet']
                description = snippet.get('description', '')
                action = video_info.get('action', 'replace')

                if action == 'replace':
                    # Verify content still needs updating
                    if not _needs_update(description):
                        successfully_processed_ids.add(vid)  # Already fixed
                        continue
                    # Apply all transformations
                    new_description = _transform_description(description)
                else:
                    # action == 'add': append new link at end of description
                    if _is_already_updated(description):
                        successfully_processed_ids.add(vid)  # Already has new link
                        continue
                    new_description = description.rstrip() + '\n\n' + NEW_URL if description.strip() else NEW_URL

                # Construct FULL snippet with ALL required fields preserved
                updated_snippet = {
                    'title': snippet['title'],
                    'description': new_description,
                    'categoryId': snippet['categoryId'],
                }
                if 'tags' in snippet:
                    updated_snippet['tags'] = snippet['tags']
                if 'defaultLanguage' in snippet:
                    updated_snippet['defaultLanguage'] = snippet['defaultLanguage']
                if 'defaultAudioLanguage' in snippet:
                    updated_snippet['defaultAudioLanguage'] = snippet['defaultAudioLanguage']

                # WRITE the update
                youtube.videos().update(
                    part='snippet',
                    body={'id': vid, 'snippet': updated_snippet}
                ).execute()

                updated.append({
                    'video_id': vid,
                    'title': video_info['title'],
                    'youtube_url': f'https://www.youtube.com/watch?v={vid}'
                })
                successfully_processed_ids.add(vid)
                print(f"[YOUTUBE] Updated: {video_info['title']}")

                time.sleep(0.5)  # Rate limit: ~2 updates/second

            except HttpError as e:
                if 'quotaExceeded' in str(e):
                    print(f"[YOUTUBE] Quota exceeded after {len(updated)} updates")
                    quota_exceeded = True
                    break
                failed.append({
                    'video_id': vid, 'title': video_info['title'],
                    'error': f'Erreur {e.resp.status}'
                })
                print(f"[YOUTUBE] Failed {vid}: {e}")
            except Exception as e:
                failed.append({
                    'video_id': vid, 'title': video_info['title'],
                    'error': str(e)
                })
                print(f"[YOUTUBE] Failed {vid}: {e}")

        # Update analysis file: remove processed videos
        remaining = [v for v in to_update if v['video_id'] not in successfully_processed_ids]
        analysis['to_update'] = remaining
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)

        _save_youtube_credentials(credentials)

        return jsonify({
            'success': True,
            'updated': updated,
            'failed': failed,
            'remaining': len(remaining),
            'quota_exceeded': quota_exceeded
        })

    except Exception as e:
        print(f"[YOUTUBE] Critical error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
