import json
import sqlite3
from flask import Blueprint, render_template, request, session, current_app

from app.db import get_db, get_songs
from app.categories import categorize_video

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    # Auto-login for testing (but not if user explicitly logged out)
    if current_app.config['AUTO_LOGIN'] and 'admin' not in session and 'logged_out' not in session:
        session['admin'] = True

    category = request.args.get('category', 'all')
    search = request.args.get('search', '').strip()
    composer_filter = request.args.get('composer', 'all')
    performer_filter = request.args.get('performer', 'all')
    style_filter = request.args.get('style', 'all')
    era_filter = request.args.get('era', 'all')
    depth_filter = request.args.get('depth', 'all')
    view = request.args.get('view', 'songs')
    sort = request.args.get('sort', 'date')

    songs = get_songs()

    # Index view - Real Book style alphabetical list
    if view == 'index':
        processed = []
        for s in songs:
            url = s['url'] or ''
            if url and s['timestamp']:
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
                'url': url,
                'analysis_depth': s['analysis_depth'] or ''
            })

        if depth_filter != 'all':
            processed = [s for s in processed if s['analysis_depth'] == depth_filter]

        processed.sort(key=lambda x: x['song_title'].lower())

        return render_template('index_view.html',
                             songs=processed,
                             depth_filter=depth_filter,
                             is_admin=session.get('admin', False))

    # Videos view
    if view == 'videos' or (not songs and session.get('admin')):
        db = get_db()
        cursor = db.cursor()
        video_order = 'published_at DESC' if sort == 'date' else 'title ASC'
        cursor.execute(f'SELECT id, title, description, url, published_at, thumbnail_url, video_type, category FROM videos ORDER BY {video_order}')
        videos = cursor.fetchall()

        video_list = []
        for v in videos:
            cursor.execute('''SELECT id, song_title, composer, performer, original_artist,
                            composition_year, style, era, album, record_label,
                            recording_year, featured_artists, context_notes,
                            part_number, total_parts
                            FROM songs WHERE video_id = ? AND (deleted IS NULL OR deleted = 0) ORDER BY part_number''', (v['id'],))
            all_songs = cursor.fetchall()

            if all_songs:
                song_data = all_songs[0]
                songs_list = [{'id': s['id'], 'song_title': s['song_title']} for s in all_songs]
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
                    'part_number': 1, 'total_parts': 1,
                    'composer': '', 'performer': '', 'original_artist': '',
                    'composition_year': None, 'style': '', 'era': '',
                    'album': '', 'record_label': '', 'recording_year': None,
                    'featured_artists': None, 'context_notes': '',
                    'extracted_songs': []
                })

        return render_template('index.html',
                             videos=video_list,
                             category='all', categories=[],
                             search=search,
                             composer_filter='all', performer_filter='all',
                             style_filter='all', era_filter='all',
                             composers=[], performers=[], styles=[], eras=[],
                             is_admin=session.get('admin', False),
                             view=view, sort=sort)

    # Songs view (default)
    processed = []
    for s in songs:
        cat = s['category'] or categorize_video(s['video_title'], s['description'])

        url = s['url']
        if s['timestamp']:
            parts = s['timestamp'].split(':')
            if len(parts) == 2:
                seconds = int(parts[0]) * 60 + int(parts[1])
                url = f"{s['url']}&t={seconds}s"

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
            'id': s['id'], 'video_id': s['video_id'],
            'title': s['song_title'], 'composer': s['composer'] or '',
            'performer': s['performer'] or '', 'original_artist': s['original_artist'] or '',
            'songwriters': songwriters, 'composition_year': s['composition_year'],
            'style': s['style'] or '', 'era': s['era'] or '',
            'other_musicians': other_musicians, 'additional_info': s['additional_info'] or '',
            'url': url, 'video_title': s['video_title'],
            'description': s['description'], 'category': cat,
            'published_at': s['published_at'],
            'part_number': s['part_number'], 'total_parts': s['total_parts'],
            'album': s['album'] or '', 'record_label': s['record_label'] or '',
            'recording_year': s['recording_year'], 'featured_artists': featured_artists,
            'context_notes': s['context_notes'] or '',
            'analysis_depth': s['analysis_depth'] or '',
            'thumbnail_url': s['thumbnail_url'],
            'video_type': s['video_type'] or 'uncategorized'
        })

    # Search filter
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

    if category != 'all':
        processed = [s for s in processed if s['category'] == category]
    if composer_filter != 'all':
        processed = [s for s in processed if s['composer'] and composer_filter.lower() in s['composer'].lower()]
    if performer_filter != 'all':
        processed = [s for s in processed if s['performer'] and performer_filter.lower() in s['performer'].lower()]
    if style_filter != 'all':
        processed = [s for s in processed if s['style'] and style_filter.lower() in s['style'].lower()]
    if era_filter != 'all':
        processed = [s for s in processed if s['era'] and era_filter.lower() in s['era'].lower()]
    if depth_filter != 'all':
        processed = [s for s in processed if s['analysis_depth'] and depth_filter == s['analysis_depth']]

    if sort == 'alpha':
        processed.sort(key=lambda x: x['title'].lower())
    else:
        processed.sort(key=lambda x: x.get('published_at') or '', reverse=True)

    # Get all unique values for filter dropdowns (from ALL songs, not just filtered)
    all_songs = get_songs()
    all_processed = []
    for s in all_songs:
        cat = categorize_video(s['video_title'], s['description'])
        all_processed.append({
            'composer': s['composer'] or '', 'performer': s['performer'] or '',
            'style': s['style'] or '', 'era': s['era'] or '',
            'category': cat, 'analysis_depth': s['analysis_depth'] or ''
        })

    return render_template('index.html',
                         videos=processed,
                         category=category,
                         categories=sorted(set(s['category'] for s in all_processed)),
                         search=search,
                         composer_filter=composer_filter,
                         performer_filter=performer_filter,
                         style_filter=style_filter,
                         era_filter=era_filter,
                         depth_filter=depth_filter,
                         composers=sorted(set(s['composer'] for s in all_processed if s['composer'])),
                         performers=sorted(set(s['performer'] for s in all_processed if s['performer'])),
                         styles=sorted(set(s['style'] for s in all_processed if s['style'])),
                         eras=sorted(set(s['era'] for s in all_processed if s['era'])),
                         depths=sorted(set(s['analysis_depth'] for s in all_processed if s['analysis_depth'])),
                         is_admin=session.get('admin', False),
                         view=view, sort=sort)
