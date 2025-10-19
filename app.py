from flask import Flask, render_template, request, session, jsonify, redirect
import sqlite3
import json
import sys
import re
import os
import shutil
import requests
import html
from datetime import datetime
from dotenv import load_dotenv
sys.path.append('config')
from admin_config import ADMIN_USERNAME, ADMIN_PASSWORD, AUTO_LOGIN, SECRET_KEY
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Database path - use persistent disk on Render, local path otherwise
if os.path.exists('/data'):
    DATABASE_PATH = '/data/piano_jazz_videos.db'
    # Copy database to persistent disk on first run
    if not os.path.exists(DATABASE_PATH):
        os.makedirs('/data', exist_ok=True)
        if os.path.exists('database/piano_jazz_videos.db'):
            shutil.copy2('database/piano_jazz_videos.db', DATABASE_PATH)
            print(f"✓ Database copied to persistent disk: {DATABASE_PATH}")
else:
    DATABASE_PATH = 'database/piano_jazz_videos.db'

print(f"Using database at: {DATABASE_PATH}")

# Auto-migration: Add category columns if they don't exist
def ensure_category_columns():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Check and add category column to videos table
    cursor.execute("PRAGMA table_info(videos)")
    videos_columns = [col[1] for col in cursor.fetchall()]
    if 'category' not in videos_columns:
        cursor.execute("ALTER TABLE videos ADD COLUMN category TEXT DEFAULT NULL")
        print("✓ Added category column to videos table")

    # Check and add category column to songs table
    cursor.execute("PRAGMA table_info(songs)")
    songs_columns = [col[1] for col in cursor.fetchall()]
    if 'category' not in songs_columns:
        cursor.execute("ALTER TABLE songs ADD COLUMN category TEXT DEFAULT NULL")
        print("✓ Added category column to songs table")

    conn.commit()
    conn.close()

ensure_category_columns()

# OpenAI client for re-extraction
openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key:
    print(f"[STARTUP] OpenAI API key loaded: {openai_api_key[:7]}...{openai_api_key[-4:]}")
else:
    print("[STARTUP] WARNING: OPENAI_API_KEY not found in environment!")
openai_client = OpenAI(
    api_key=openai_api_key
)

def get_songs():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            s.id,
            s.video_id,
            s.song_title,
            s.composer,
            s.timestamp,
            s.part_number,
            s.total_parts,
            s.performer,
            s.original_artist,
            s.songwriters,
            s.composition_year,
            s.style,
            s.era,
            s.other_musicians,
            s.additional_info,
            s.video_title,
            s.video_url as url,
            s.video_description as description,
            s.published_at,
            s.album,
            s.record_label,
            s.recording_year,
            s.featured_artists,
            s.context_notes,
            v.thumbnail_url,
            v.video_type,
            COALESCE(s.category, v.category) as category
        FROM songs s
        LEFT JOIN videos v ON s.video_id = v.id
        ORDER BY s.song_title ASC
    ''')
    songs = cursor.fetchall()
    conn.close()
    return songs

def categorize_video(title, description):
    """Categorize videos by type"""
    title_lower = title.lower()
    desc_lower = description.lower()

    # Generics/TV themes
    if any(word in title_lower for word in ['générique', 'magnum', 'mission impossible', 'james bond', 'star trek', 'code quantum', 'amicalement vôtre', 'quatrième dimension', 'cinéma du dimanche']):
        return 'Génériques TV'

    # Movie soundtracks
    if any(word in title_lower for word in ['mission to mars', 'morricone', 'yared', 'legrand', 'cosma', 'b.o', 'costa yared']):
        return 'BO Films'

    # Songs
    if any(word in title_lower for word in ['que je t\'aime', 'pénitencier', 'yesterday', 'nature boy', 'embraceable you', 'my funny valentine', 'all of you', 'satin doll', 'marseillaise', 'god save', 'skylark', 'etienne', 'vivre quand on aime', 'kamasutra']):
        return 'Chansons/Standards'

    # Video games
    if any(word in title_lower for word in ['jeux vidéo', 'goldeneye', 'mario', 'videogames']):
        return 'Jeux Vidéo'

    # Analysis/Theory
    if any(word in title_lower for word in ['analyse', 'harmoni', 'modal', 'accord', 'improvisation', 'technique', 'concept', 'appoggiature', 'cadence', 'gamme', 'échelle', 'dorien', 'ionien', 'phrygien', 'lydien', 'mixolydien', 'éolien', 'locrien']):
        return 'Théorie/Analyse'

    # Interviews/Culture
    if any(word in title_lower for word in ['chronique', 'interview', 'culture', 'avec', 'galper', 'terrasson', 'bojan', 'paczynski', 'naïditch', 'quincy jones', 'lucas debargue']):
        return 'Interviews/Culture'

    return 'Autres'

@app.route('/')
def index():
    # Auto-login for testing (but not if user explicitly logged out)
    if AUTO_LOGIN and 'admin' not in session and 'logged_out' not in session:
        session['admin'] = True

    category = request.args.get('category', 'all')
    search = request.args.get('search', '').strip()
    composer_filter = request.args.get('composer', 'all')
    performer_filter = request.args.get('performer', 'all')
    style_filter = request.args.get('style', 'all')
    era_filter = request.args.get('era', 'all')
    view = request.args.get('view', 'songs')

    songs = get_songs()

    # Index view - Real Book style alphabetical list
    if view == 'index':
        # Get all songs, sorted alphabetically
        processed = []
        for s in songs:
            # Build URL with timestamp
            url = s['url'] or ''
            if url and s['timestamp']:
                # Convert MM:SS to seconds
                timestamp = s['timestamp']
                if timestamp and ':' in timestamp:
                    parts = timestamp.split(':')
                    if len(parts) == 2:
                        try:
                            minutes = int(parts[0])
                            seconds = int(parts[1])
                            total_seconds = minutes * 60 + seconds
                            url = f"{url}&t={total_seconds}s"
                        except ValueError:
                            pass

            processed.append({
                'id': s['id'],
                'song_title': s['song_title'] or 'Sans titre',
                'composer': s['composer'] or '',
                'performer': s['performer'] or '',
                'album': s['album'] or '',
                'style': s['style'] or '',
                'url': url
            })

        # Sort alphabetically by song title
        processed.sort(key=lambda x: x['song_title'].lower())

        return render_template('index_view.html',
                             songs=processed,
                             is_admin=session.get('admin', False))

    # If view=videos or no songs, show videos instead for re-extraction
    if (view == 'videos' or not songs) and session.get('admin'):
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, description, url, published_at, thumbnail_url, video_type, category FROM videos ORDER BY title ASC')
        videos = cursor.fetchall()

        video_list = []
        for v in videos:
            # Try to fetch ALL extracted songs for this video
            cursor.execute('''SELECT id, song_title, composer, performer, original_artist,
                            composition_year, style, era, album, record_label,
                            recording_year, featured_artists, context_notes,
                            part_number, total_parts
                            FROM songs WHERE video_id = ? AND (deleted IS NULL OR deleted = 0) ORDER BY part_number''', (v['id'],))
            all_songs = cursor.fetchall()

            if all_songs:
                # Get first song for metadata display
                song_data = all_songs[0]
                # Convert all_songs to list of dicts
                songs_list = [{
                    'id': s['id'],
                    'song_title': s['song_title']
                } for s in all_songs]

                # Use extracted song metadata
                video_list.append({
                    'id': None,
                    'video_id': v['id'],
                    'title': v['title'],
                    'url': v['url'],
                    'video_title': v['title'],
                    'description': v['description'],
                    'published_at': v['published_at'],
                    'thumbnail_url': v['thumbnail_url'],
                    'video_type': v['video_type'] or 'uncategorized',
                    'category': v['category'] or categorize_video(v['title'], v['description']),
                    'part_number': song_data['part_number'] or 1,
                    'total_parts': song_data['total_parts'] or 1,
                    'composer': song_data['composer'] or '',
                    'performer': song_data['performer'] or '',
                    'original_artist': song_data['original_artist'] or '',
                    'composition_year': song_data['composition_year'],
                    'style': song_data['style'] or '',
                    'era': song_data['era'] or '',
                    'album': song_data['album'] or '',
                    'record_label': song_data['record_label'] or '',
                    'recording_year': song_data['recording_year'],
                    'featured_artists': song_data['featured_artists'],
                    'context_notes': song_data['context_notes'] or '',
                    'extracted_songs': songs_list
                })
            else:
                # No songs extracted yet - show placeholder
                video_list.append({
                    'id': None,
                    'video_id': v['id'],
                    'title': v['title'],
                    'url': v['url'],
                    'video_title': v['title'],
                    'description': v['description'],
                    'published_at': v['published_at'],
                    'thumbnail_url': v['thumbnail_url'],
                    'video_type': v['video_type'] or 'uncategorized',
                    'category': v['category'] or categorize_video(v['title'], v['description']),
                    'part_number': 1,
                    'total_parts': 1,
                    'composer': '',
                    'performer': '',
                    'original_artist': '',
                    'composition_year': None,
                    'style': '',
                    'era': '',
                    'album': '',
                    'record_label': '',
                    'recording_year': None,
                    'featured_artists': None,
                    'context_notes': 'Click Re-extract to populate metadata',
                    'extracted_songs': []
                })

        conn.close()

        return render_template('index.html',
                             videos=video_list,
                             category='all',
                             categories=[],
                             search=search,
                             composer_filter='all',
                             performer_filter='all',
                             style_filter='all',
                             era_filter='all',
                             composers=[],
                             performers=[],
                             styles=[],
                             eras=[],
                             is_admin=session.get('admin', False),
                             view=view)

    # Process songs
    processed = []
    for s in songs:
        cat = s['category'] or categorize_video(s['video_title'], s['description'])

        # Build URL with timestamp if available
        url = s['url']
        if s['timestamp']:
            # Convert timestamp to seconds for YouTube URL
            parts = s['timestamp'].split(':')
            if len(parts) == 2:
                seconds = int(parts[0]) * 60 + int(parts[1])
                url = f"{s['url']}&t={seconds}s"

        # Parse JSON fields
        songwriters = None
        other_musicians = None
        featured_artists = None
        try:
            if s['songwriters']:
                songwriters = json.loads(s['songwriters'])
            if s['other_musicians']:
                other_musicians = json.loads(s['other_musicians'])
            if s['featured_artists']:
                featured_artists = json.loads(s['featured_artists'])
        except:
            pass

        processed.append({
            'id': s['id'],
            'video_id': s['video_id'],
            'title': s['song_title'],
            'composer': s['composer'] or '',
            'performer': s['performer'] or '',
            'original_artist': s['original_artist'] or '',
            'songwriters': songwriters,
            'composition_year': s['composition_year'],
            'style': s['style'] or '',
            'era': s['era'] or '',
            'other_musicians': other_musicians,
            'additional_info': s['additional_info'] or '',
            'url': url,
            'video_title': s['video_title'],
            'description': s['description'],
            'category': cat,
            'published_at': s['published_at'],
            'part_number': s['part_number'],
            'total_parts': s['total_parts'],
            'album': s['album'] or '',
            'record_label': s['record_label'] or '',
            'recording_year': s['recording_year'],
            'featured_artists': featured_artists,
            'context_notes': s['context_notes'] or '',
            'thumbnail_url': s['thumbnail_url'],
            'video_type': s['video_type'] or 'uncategorized'
        })

    # Search filter - now searches across all enriched fields
    if search:
        search_lower = search.lower()
        processed = [s for s in processed if
                    search_lower in s['title'].lower() or
                    search_lower in (s['composer'] or '').lower() or
                    search_lower in (s['performer'] or '').lower() or
                    search_lower in (s['original_artist'] or '').lower() or
                    search_lower in (s['style'] or '').lower() or
                    search_lower in (s['era'] or '').lower() or
                    search_lower in (s['album'] or '').lower() or
                    search_lower in (s['record_label'] or '').lower() or
                    search_lower in s['video_title'].lower()]

    # Filter by category
    if category != 'all':
        processed = [s for s in processed if s['category'] == category]

    # Filter by composer
    if composer_filter != 'all':
        processed = [s for s in processed if s['composer'] and composer_filter.lower() in s['composer'].lower()]

    # Filter by performer
    if performer_filter != 'all':
        processed = [s for s in processed if s['performer'] and performer_filter.lower() in s['performer'].lower()]

    # Filter by style
    if style_filter != 'all':
        processed = [s for s in processed if s['style'] and style_filter.lower() in s['style'].lower()]

    # Filter by era
    if era_filter != 'all':
        processed = [s for s in processed if s['era'] and era_filter.lower() in s['era'].lower()]

    # Default sort: alphabetical by title
    processed.sort(key=lambda x: x['title'].lower())

    # Get all unique values for filter dropdowns (from ALL songs, not just filtered)
    all_songs = get_songs()
    all_processed = []
    for s in all_songs:
        cat = categorize_video(s['video_title'], s['description'])
        all_processed.append({
            'composer': s['composer'] or '',
            'performer': s['performer'] or '',
            'style': s['style'] or '',
            'era': s['era'] or '',
            'category': cat
        })

    all_categories = sorted(set(s['category'] for s in all_processed))
    all_composers = sorted(set(s['composer'] for s in all_processed if s['composer']))
    all_performers = sorted(set(s['performer'] for s in all_processed if s['performer']))
    all_styles = sorted(set(s['style'] for s in all_processed if s['style']))
    all_eras = sorted(set(s['era'] for s in all_processed if s['era']))

    return render_template('index.html',
                         videos=processed,
                         category=category,
                         categories=all_categories,
                         search=search,
                         composer_filter=composer_filter,
                         performer_filter=performer_filter,
                         style_filter=style_filter,
                         era_filter=era_filter,
                         composers=all_composers,
                         performers=all_performers,
                         styles=all_styles,
                         eras=all_eras,
                         is_admin=session.get('admin', False),
                         view=view)

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if data.get('username') == ADMIN_USERNAME and data.get('password') == ADMIN_PASSWORD:
        session['admin'] = True
        session.pop('logged_out', None)  # Clear logout flag

        # Handle "Remember Me" - make session permanent (lasts 30 days)
        if data.get('remember'):
            session.permanent = True
        else:
            session.permanent = False

        return jsonify({'success': True})
    return jsonify({'success': False}), 401

@app.route('/logout')
def logout():
    session.pop('admin', None)
    session['logged_out'] = True
    return redirect('/')

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('admin', None)
    session['logged_out'] = True
    return jsonify({'success': True})

@app.route('/api/update_song', methods=['POST'])
def update_song():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    song_id = data.get('id')
    field = data.get('field')
    value = data.get('value')

    # Validate field name to prevent SQL injection
    allowed_fields = ['song_title', 'composer', 'performer', 'original_artist',
                     'composition_year', 'style', 'era', 'additional_info',
                     'album', 'record_label', 'recording_year', 'context_notes']

    if field not in allowed_fields:
        return jsonify({'success': False, 'error': 'Invalid field'}), 400

    try:
        conn = sqlite3.connect(DATABASE_PATH, timeout=10.0)
        cursor = conn.cursor()
        cursor.execute(f'UPDATE songs SET {field} = ? WHERE id = ?', (value, song_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except sqlite3.OperationalError as e:
        if 'locked' in str(e):
            return jsonify({'success': False, 'error': 'Database is locked. Enrichment script is running. Please try again later.'}), 503
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_master_prompt', methods=['GET'])
def get_master_prompt():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    try:
        with open('config/prompt_template.txt', 'r') as f:
            prompt = f.read()
        return jsonify({'success': True, 'prompt': prompt})
    except FileNotFoundError:
        # Return default prompt if file doesn't exist
        default_prompt = open('utils/llm_full_extract.py', 'r').read()
        # Extract prompt from the file
        start = default_prompt.find('prompt = f"""') + 13
        end = default_prompt.find('"""', start)
        prompt_text = default_prompt[start:end]
        return jsonify({'success': True, 'prompt': prompt_text})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update_category', methods=['POST'])
def update_category():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    item_id = data.get('id')
    category = data.get('category')
    view = data.get('view', 'songs')  # 'songs' or 'videos'

    if not item_id or not category:
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Update the appropriate table based on view
        if view == 'videos':
            cursor.execute('UPDATE videos SET category = ? WHERE id = ?', (category, item_id))
        else:  # songs view
            cursor.execute('UPDATE songs SET category = ? WHERE id = ?', (category, item_id))

        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete_song', methods=['POST'])
def delete_song():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    song_id = data.get('song_id')

    if not song_id:
        return jsonify({'success': False, 'error': 'Missing song_id'}), 400

    try:
        conn = sqlite3.connect(DATABASE_PATH, timeout=10.0)
        cursor = conn.cursor()

        # Soft delete: mark as deleted instead of actually deleting
        cursor.execute('UPDATE songs SET deleted = 1 WHERE id = ?', (song_id,))
        conn.commit()
        conn.close()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/restore_song', methods=['POST'])
def restore_song():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    song_id = data.get('song_id')

    if not song_id:
        return jsonify({'success': False, 'error': 'Missing song_id'}), 400

    try:
        conn = sqlite3.connect(DATABASE_PATH, timeout=10.0)
        cursor = conn.cursor()

        # Restore: unmark as deleted
        cursor.execute('UPDATE songs SET deleted = 0 WHERE id = ?', (song_id,))
        conn.commit()
        conn.close()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/enrich_video', methods=['POST'])
def enrich_video():
    """Extract songs from a video using LLM"""
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    video_id = data.get('video_id')

    if not video_id:
        return jsonify({'success': False, 'error': 'Missing video_id'}), 400

    try:
        conn = sqlite3.connect(DATABASE_PATH, timeout=10.0)
        cursor = conn.cursor()

        # Get video details
        cursor.execute('''
            SELECT title, description, url
            FROM videos
            WHERE id = ?
        ''', (video_id,))

        video = cursor.fetchone()
        if not video:
            conn.close()
            return jsonify({'success': False, 'error': 'Video not found'}), 404

        video_title, video_description, video_url = video

        # Extract songs using LLM
        print(f"[ENRICH] Extracting songs from: {video_title}")
        songs = extract_video_data_for_auto_update(video_title, video_description, video_url)

        # Delete existing songs for this video
        cursor.execute('DELETE FROM songs WHERE video_id = ?', (video_id,))

        # Insert new songs
        for song in songs:
            cursor.execute('''
                INSERT INTO songs (
                    video_id, song_title, composer, performer, original_artist,
                    album, record_label, recording_year, composition_year,
                    style, era, featured_artists, context_notes, timestamp,
                    part_number, total_parts, video_title, video_url,
                    video_description, published_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_id,
                song.get('song_title'),
                song.get('composer'),
                song.get('performer'),
                song.get('original_artist'),
                song.get('album'),
                song.get('record_label'),
                song.get('recording_year'),
                song.get('composition_year'),
                song.get('style'),
                song.get('era'),
                ', '.join(song.get('featured_artists', [])) if song.get('featured_artists') else None,
                song.get('context_notes'),
                song.get('timestamp'),
                song.get('part_number', 1),
                song.get('total_parts', 1),
                video_title,
                video_url,
                video_description,
                None  # published_at - not available in this context
            ))

        conn.commit()
        conn.close()

        print(f"[ENRICH] Extracted {len(songs)} song(s)")
        return jsonify({'success': True, 'songs_count': len(songs)})

    except Exception as e:
        print(f"[ENRICH] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/create_song', methods=['POST'])
def create_song():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    video_id = data.get('video_id')
    song_title = data.get('song_title')

    if not video_id or not song_title:
        return jsonify({'success': False, 'error': 'Missing video_id or song_title'}), 400

    try:
        conn = sqlite3.connect(DATABASE_PATH, timeout=10.0)
        cursor = conn.cursor()

        # Get video information
        cursor.execute('''
            SELECT id, title, description, url, thumbnail_url, published_at
            FROM videos
            WHERE id = ?
        ''', (video_id,))
        video = cursor.fetchone()

        if not video:
            conn.close()
            return jsonify({'success': False, 'error': 'Video not found'}), 404

        # Insert new song with minimal data
        cursor.execute('''
            INSERT INTO songs (
                video_id, song_title, video_title, video_url,
                video_description, published_at, part_number, total_parts, deleted
            ) VALUES (?, ?, ?, ?, ?, ?, 1, 1, 0)
        ''', (
            video[0],  # video_id
            song_title,  # song_title
            video[1],  # video_title
            video[3],  # video_url
            video[2],  # video_description
            video[5]   # published_at
        ))

        new_song_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'song_id': new_song_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_changelog', methods=['GET'])
def get_changelog():
    try:
        changelog_path = 'CHANGELOG.md'
        if not os.path.exists(changelog_path):
            return jsonify({'success': True, 'updates': [], 'count': 0})

        # Get last seen timestamp from session (default to 0 for first visit)
        last_seen = session.get('changelog_last_seen', 0)

        # Parse changelog file with new format
        updates = []
        current_date = None
        current_section = None

        with open(changelog_path, 'r', encoding='utf-8') as f:
            for line in f:
                line_stripped = line.strip()

                # Match date headers like "## 2025-10-02"
                if line_stripped.startswith('## ') and len(line_stripped) > 3:
                    date_str = line_stripped[3:].strip()
                    # Skip non-date headers like "Summary Statistics"
                    if date_str[0].isdigit():
                        try:
                            # Parse date without time (assume end of day for comparison)
                            entry_time = datetime.strptime(date_str, '%Y-%m-%d').replace(hour=23, minute=59).timestamp()

                            # Start new date entry
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

                # Match section headers like "### UI/UX Improvements"
                elif line_stripped.startswith('### ') and current_date:
                    section_name = line_stripped[4:].strip()
                    current_section = section_name
                    current_date['sections'][section_name] = []

                # Match bullet points like "- Feature description (commit)"
                elif line_stripped.startswith('- ') and current_date:
                    change = line_stripped[2:].strip()
                    # If no section yet, put in "General" section
                    if not current_section:
                        if 'Général' not in current_date['sections']:
                            current_date['sections']['Général'] = []
                        current_date['sections']['Général'].append(change)
                    else:
                        current_date['sections'][current_section].append(change)

        # Count new updates (dates, not individual changes)
        new_count = sum(1 for u in updates if u['is_new'])

        return jsonify({
            'success': True,
            'updates': updates,
            'count': new_count
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/mark_changelog_seen', methods=['POST'])
def mark_changelog_seen():
    try:
        # Store current timestamp as last seen
        session['changelog_last_seen'] = datetime.now().timestamp()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auto_update', methods=['POST'])
def auto_update():
    """
    Auto-update endpoint that:
    1. Scrapes YouTube for latest videos
    2. Extracts songs from new videos using LLM
    """
    try:
        # Get API keys from environment
        youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        openai_api_key = os.getenv('OPENAI_API_KEY')

        if not youtube_api_key or not openai_api_key:
            return jsonify({
                'success': False,
                'error': 'API keys not configured'
            }), 500

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # STEP 1: Scrape YouTube for videos
        channel_handle = 'Pianojazzconcept'

        # Get channel ID
        search = requests.get('https://www.googleapis.com/youtube/v3/search', params={
            'key': youtube_api_key,
            'q': channel_handle,
            'type': 'channel',
            'part': 'snippet'
        }).json()

        if 'items' not in search or len(search['items']) == 0:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Channel not found'
            }), 404

        channel_id = search['items'][0]['id']['channelId']

        # Get existing video IDs to detect new videos
        cursor.execute('SELECT video_id FROM videos')
        existing_video_ids = set(row[0] for row in cursor.fetchall())

        # Fetch latest videos (first page only - 50 videos)
        new_videos = []
        videos_to_extract = []  # Videos needing song extraction (new or with 0 songs)

        params = {
            'key': youtube_api_key,
            'channelId': channel_id,
            'part': 'snippet',
            'type': 'video',
            'maxResults': 50,
            'order': 'date'
        }

        response = requests.get('https://www.googleapis.com/youtube/v3/search', params=params).json()

        # Collect video IDs
        video_ids = [item['id']['videoId'] for item in response.get('items', [])]

        # Fetch full details including complete descriptions
        if video_ids:
            details_response = requests.get('https://www.googleapis.com/youtube/v3/videos', params={
                'key': youtube_api_key,
                'id': ','.join(video_ids),
                'part': 'snippet'
            }).json()

            for item in details_response.get('items', []):
                video_id = item['id']
                title = html.unescape(item['snippet']['title'])
                description = html.unescape(item['snippet']['description'])
                url = f"https://youtube.com/watch?v={video_id}"
                published_at = item['snippet']['publishedAt']

                # Get highest quality thumbnail available
                thumbnails = item['snippet']['thumbnails']
                thumbnail_url = (thumbnails.get('maxres') or
                               thumbnails.get('high') or
                               thumbnails.get('medium') or
                               thumbnails.get('default'))['url']

                # Check if this is a new video
                is_new = video_id not in existing_video_ids

                cursor.execute('''
                    INSERT OR REPLACE INTO videos (video_id, title, description, url, published_at, thumbnail_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (video_id, title, description, url, published_at, thumbnail_url))

                db_video_id = cursor.lastrowid

                if is_new:
                    new_videos.append({
                        'id': db_video_id,
                        'video_id': video_id,
                        'title': title,
                        'description': description,
                        'url': url
                    })
                    videos_to_extract.append({
                        'id': db_video_id,
                        'video_id': video_id,
                        'title': title,
                        'description': description,
                        'url': url
                    })
                else:
                    # Check if existing video has 0 songs
                    cursor.execute('SELECT id FROM videos WHERE video_id = ?', (video_id,))
                    db_row = cursor.fetchone()
                    if db_row:
                        db_video_id = db_row[0]
                        cursor.execute('SELECT COUNT(*) FROM songs WHERE video_id = ?', (db_video_id,))
                        song_count = cursor.fetchone()[0]

                        if song_count == 0:
                            print(f"[AUTO-UPDATE] Video has 0 songs, will re-extract: {title}")
                            videos_to_extract.append({
                                'id': db_video_id,
                                'video_id': video_id,
                                'title': title,
                                'description': description,
                                'url': url
                            })

        conn.commit()

        # STEP 2: Extract songs from videos needing extraction (new or with 0 songs)
        new_songs_count = 0

        if videos_to_extract:
            for video in videos_to_extract:
                # Use the same extraction logic from llm_full_extract.py
                songs = extract_video_data_for_auto_update(
                    video['title'],
                    video['description'] or '',
                    video['url']
                )

                if songs:
                    for song_idx, song in enumerate(songs, 1):
                        # Convert featured_artists list to JSON string
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
                            video['id'],
                            song.get('song_title', video['title']),
                            song.get('composer'),
                            song.get('performer'),
                            song.get('original_artist'),
                            song.get('timestamp'),
                            song.get('composition_year'),
                            song.get('style'),
                            song.get('era'),
                            song.get('additional_info'),
                            song_idx,
                            len(songs),
                            song.get('album'),
                            song.get('record_label'),
                            song.get('recording_year'),
                            featured_artists,
                            song.get('context_notes'),
                            video['title'],
                            video['url'],
                            video['description'],
                            None
                        ))

                    new_songs_count += len(songs)

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'new_videos': len(new_videos),
            'new_songs': new_songs_count,
            'message': f'Found {len(new_videos)} new video(s), extracted {new_songs_count} song(s)'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def extract_video_data_for_auto_update(video_title, video_description, video_url, prompt_guidance=''):
    """
    Extract video data using LLM - uses same prompt as llm_full_extract.py
    """
    # Use the exact same prompt as llm_full_extract.py
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

IMPORTANT - BE CONSERVATIVE:
- ONLY extract songs that are CLEARLY mentioned in title or description
- If video is theory/discussion with NO SPECIFIC SONGS → return empty array []
- DO NOT make up songs or use generic examples
- DO NOT default to any particular song if unclear
- If unsure → return empty array []

YOUR TASK:
Extract ALL songs/pieces analyzed in this video with MAXIMUM metadata.

Use THREE sources:
1. Video title/description to identify songs and artists
2. Your training data to fill gaps and add context
3. Your knowledge of jazz history, famous recordings, albums, etc.

EXTRACT EVERYTHING (but only if songs are clearly present):
- Song title (MUST be explicitly mentioned in title/description)
- Composer(s)
- Performer/Artist (whose recording/version is being analyzed - NEVER Étienne)
  - From title: "avec Brad Mehldau" → Brad Mehldau
  - From description: "analyse du solo de Coltrane" → John Coltrane
  - If song mentioned but no performer → use your knowledge to identify famous version
  - If no specific recording mentioned → leave null
- Original artist (if it's a cover/arrangement)
- Album name (if mentioned OR if you know which famous album)
- Record label (if you know it)
- Recording year (if mentioned OR if you know the famous recording year)
- Composition year
- Style/genre
- Era/decade
- Featured artists (all artists mentioned in title/description)
- Context notes (analyzing specific recording? comparing versions? theory video?)
- Timestamp (if provided)

MULTIPLE VERSIONS:
If video compares/analyzes multiple artists' versions, create SEPARATE entries

NO LIMITATIONS:
Add as much information as you can from your training data. If you know the song:
- Famous recordings and their details
- Historical context
- Notable musicians
- Anything valuable for cataloging

Return JSON array:
- If songs found: return array with song objects
- If NO songs mentioned/analyzed: return empty array []
- Even if single song, return array with 1 item

Example response:
[
  {{
    "song_title": "song name",
    "composer": "who wrote it",
    "performer": "whose recording is analyzed (NEVER Étienne)",
    "original_artist": "if it's a cover",
    "album": "album name if known",
    "record_label": "label if known",
    "recording_year": year or null,
    "composition_year": year or null,
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
        print(f"[AUTO-UPDATE] Extracting songs from: {video_title}")
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a music metadata extraction expert specializing in jazz. Return only valid JSON arrays. Use your full training knowledge to add comprehensive metadata."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=2000,
            timeout=60.0  # 60 second timeout for Render
        )

        response_content = response.choices[0].message.content
        print(f"[AUTO-UPDATE] LLM Response: {response_content[:200]}...")

        # Strip markdown code blocks if present
        if response_content.startswith('```'):
            lines = response_content.split('\n')
            response_content = '\n'.join(lines[1:-1])

        result = json.loads(response_content)
        songs = result if isinstance(result, list) else [result]
        print(f"[AUTO-UPDATE] Extracted {len(songs)} song(s)")
        return songs

    except Exception as e:
        import traceback
        import sys
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"[AUTO-UPDATE] Error extracting video data ({error_type}): {error_msg}", file=sys.stderr)
        print(f"[AUTO-UPDATE] Full traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return []

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)