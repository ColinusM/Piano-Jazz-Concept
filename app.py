from flask import Flask, render_template, request, session, jsonify
import sqlite3
import json
import sys
sys.path.append('config')
from admin_config import ADMIN_USERNAME, ADMIN_PASSWORD, AUTO_LOGIN, SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY

def get_songs():
    conn = sqlite3.connect('database/piano_jazz_videos.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            id,
            song_title,
            composer,
            timestamp,
            part_number,
            total_parts,
            performer,
            original_artist,
            songwriters,
            composition_year,
            style,
            era,
            other_musicians,
            additional_info,
            video_title,
            video_url as url,
            video_description as description,
            published_at
        FROM songs
        ORDER BY song_title ASC
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
    # Auto-login for testing
    if AUTO_LOGIN and 'admin' not in session:
        session['admin'] = True

    sort = request.args.get('sort', 'alpha')
    category = request.args.get('category', 'all')
    search = request.args.get('search', '').strip()
    video_type = request.args.get('type', 'all')  # all, compilation, single, non-analysis
    composer_filter = request.args.get('composer', 'all')
    performer_filter = request.args.get('performer', 'all')
    style_filter = request.args.get('style', 'all')
    era_filter = request.args.get('era', 'all')

    songs = get_songs()

    # Process songs
    processed = []
    for s in songs:
        cat = categorize_video(s['video_title'], s['description'])

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
        try:
            if s['songwriters']:
                songwriters = json.loads(s['songwriters'])
            if s['other_musicians']:
                other_musicians = json.loads(s['other_musicians'])
        except:
            pass

        processed.append({
            'id': s['id'],
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
            'total_parts': s['total_parts']
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
                    search_lower in s['video_title'].lower()]

    # Filter by category
    if category != 'all':
        processed = [s for s in processed if s['category'] == category]

    # Filter by video type
    if video_type == 'compilation':
        processed = [s for s in processed if s['total_parts'] > 1]
    elif video_type == 'single':
        processed = [s for s in processed if s['total_parts'] == 1 and s['category'] not in ['Interviews/Culture', 'Autres']]
    elif video_type == 'non-analysis':
        # Only show first part of each video to avoid duplicates
        processed = [s for s in processed if s['category'] in ['Interviews/Culture', 'Autres'] and s['part_number'] == 1]

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

    # Sort
    if sort == 'alpha':
        processed.sort(key=lambda x: x['title'].lower())
    elif sort == 'theme':
        processed.sort(key=lambda x: (x['category'], x['title'].lower()))
    elif sort == 'date':
        processed.sort(key=lambda x: x['published_at'], reverse=True)

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
                         sort=sort,
                         category=category,
                         categories=all_categories,
                         search=search,
                         video_type=video_type,
                         composer_filter=composer_filter,
                         performer_filter=performer_filter,
                         style_filter=style_filter,
                         era_filter=era_filter,
                         composers=all_composers,
                         performers=all_performers,
                         styles=all_styles,
                         eras=all_eras,
                         is_admin=session.get('admin', False))

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if data.get('username') == ADMIN_USERNAME and data.get('password') == ADMIN_PASSWORD:
        session['admin'] = True
        return jsonify({'success': True})
    return jsonify({'success': False}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('admin', None)
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
                     'composition_year', 'style', 'era', 'additional_info']

    if field not in allowed_fields:
        return jsonify({'success': False, 'error': 'Invalid field'}), 400

    try:
        conn = sqlite3.connect('database/piano_jazz_videos.db', timeout=10.0)
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

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)