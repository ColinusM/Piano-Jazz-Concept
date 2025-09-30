from flask import Flask, render_template, request
import sqlite3
import json

app = Flask(__name__)

def get_songs():
    conn = sqlite3.connect('database/piano_jazz_videos.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            s.id,
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
            v.title as video_title,
            v.url,
            v.description,
            v.published_at
        FROM songs s
        JOIN videos v ON s.video_id = v.id
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
    sort = request.args.get('sort', 'alpha')
    category = request.args.get('category', 'all')
    search = request.args.get('search', '').strip()
    video_type = request.args.get('type', 'all')  # all, compilation, single, non-analysis

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

    # Sort
    if sort == 'alpha':
        processed.sort(key=lambda x: x['title'].lower())
    elif sort == 'theme':
        processed.sort(key=lambda x: (x['category'], x['title'].lower()))
    elif sort == 'date':
        processed.sort(key=lambda x: x['published_at'], reverse=True)

    # Get categories for filter
    all_categories = sorted(set(s['category'] for s in processed))

    return render_template('index.html',
                         videos=processed,
                         sort=sort,
                         category=category,
                         categories=all_categories,
                         search=search,
                         video_type=video_type)

if __name__ == '__main__':
    app.run(debug=True, port=5000)