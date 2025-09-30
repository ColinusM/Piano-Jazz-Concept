from flask import Flask, render_template, request, session, jsonify
import sqlite3
import json
import sys
import re
sys.path.append('config')
from admin_config import ADMIN_USERNAME, ADMIN_PASSWORD, AUTO_LOGIN, SECRET_KEY
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)
app.secret_key = SECRET_KEY

# OpenAI client for re-extraction
openai_client = OpenAI(
    api_key="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"
)

def get_songs():
    conn = sqlite3.connect('database/piano_jazz_videos.db')
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
            v.video_type
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
    view = request.args.get('view', 'songs')

    songs = get_songs()

    # If view=videos or no songs, show videos instead for re-extraction
    if (view == 'videos' or not songs) and session.get('admin'):
        conn = sqlite3.connect('database/piano_jazz_videos.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, description, url, published_at, thumbnail_url, video_type FROM videos ORDER BY title ASC')
        videos = cursor.fetchall()
        conn.close()

        video_list = []
        for v in videos:
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
                'category': 'No songs extracted yet',
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
                'context_notes': 'Click Re-extract to populate metadata'
            })

        return render_template('index.html',
                             videos=video_list,
                             sort=sort,
                             category='all',
                             categories=[],
                             search=search,
                             video_type=video_type,
                             composer_filter='all',
                             performer_filter='all',
                             style_filter='all',
                             era_filter='all',
                             composers=[],
                             performers=[],
                             styles=[],
                             eras=[],
                             is_admin=session.get('admin', False))

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

    # Filter by video type
    if video_type != 'all':
        processed = [s for s in processed if s.get('video_type') == video_type]

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
                     'composition_year', 'style', 'era', 'additional_info',
                     'album', 'record_label', 'recording_year', 'context_notes']

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

@app.route('/api/save_master_prompt', methods=['POST'])
def save_master_prompt():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    prompt = data.get('prompt')

    if not prompt:
        return jsonify({'success': False, 'error': 'Missing prompt'}), 400

    try:
        with open('config/prompt_template.txt', 'w') as f:
            f.write(prompt)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reextract_video', methods=['POST'])
def reextract_video():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    video_id = data.get('video_id')
    guidance = data.get('guidance', '').strip()

    if not video_id:
        return jsonify({'success': False, 'error': 'Missing video_id'}), 400

    try:
        conn = sqlite3.connect('database/piano_jazz_videos.db', timeout=10.0)
        cursor = conn.cursor()

        # Get video data
        cursor.execute('SELECT id, title, description, url FROM videos WHERE id = ?', (video_id,))
        video = cursor.fetchone()

        if not video:
            return jsonify({'success': False, 'error': 'Video not found'}), 404

        vid_id, title, description, url = video

        # Add guidance section if provided
        guidance_section = ""
        if guidance:
            guidance_section = f"\n\nADDITIONAL GUIDANCE FROM USER:\n{guidance}\n"

        # Run LLM extraction (same prompt as llm_full_extract.py)
        prompt = f"""You are analyzing a Piano Jazz Concept YouTube video to catalog which songs/pieces have been analyzed.

VIDEO TITLE: {title}
VIDEO URL: {url}
FULL DESCRIPTION:
{description or ''}

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

Be comprehensive BUT conservative! Only extract what's actually there.

{guidance_section}"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a music metadata extraction expert specializing in jazz. Return only valid JSON arrays. Use your full training knowledge to add comprehensive metadata."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=2000
        )

        response_content = response.choices[0].message.content

        # Strip markdown code blocks if present
        if response_content.startswith('```'):
            lines = response_content.split('\n')
            response_content = '\n'.join(lines[1:-1])

        songs = json.loads(response_content)
        if not isinstance(songs, list):
            songs = [songs]

        # Delete old songs for this video
        cursor.execute('DELETE FROM songs WHERE video_id = ?', (vid_id,))

        # Insert new songs
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
                vid_id,
                song.get('song_title', title),
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
                title,
                url,
                description,
                None
            ))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'songs_extracted': len(songs)})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_transcript', methods=['POST'])
def get_transcript():
    print("=== TRANSCRIPT REQUEST RECEIVED ===")
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    video_url = data.get('video_url')
    print(f"Video URL: {video_url}")

    if not video_url:
        return jsonify({'success': False, 'error': 'Missing video_url'}), 400

    try:
        # Extract video ID from URL
        match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', video_url)
        if not match:
            return jsonify({'success': False, 'error': 'Invalid YouTube URL'}), 400

        video_id = match.group(1)
        print(f"Video ID: {video_id}")

        # Try to fetch transcript using YouTubeTranscriptApi instance
        transcript_list = None
        error_messages = []

        try:
            api = YouTubeTranscriptApi()
            available_transcripts = api.list(video_id)

            # Try to get French first, then English
            for transcript_info in available_transcripts:
                if transcript_info.language_code in ['fr', 'en']:
                    transcript_list = api.fetch(video_id, [transcript_info.language_code])
                    print(f"✓ Found {transcript_info.language_code} transcript for {video_id}")
                    break

        except Exception as e:
            error_messages.append(f"Error: {str(e)}")
            print(f"✗ Transcript fetch failed for {video_id}: {e}")

        if not transcript_list:
            error_msg = f'No transcript available for video {video_id}. This video may not have captions/subtitles enabled.\n\nDetails:\n' + '\n'.join(error_messages)
            print(f"❌ No transcript found for {video_id}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 404

        # Format transcript as text
        transcript_text = '\n'.join([f"[{entry.start:.1f}s] {entry.text}" for entry in transcript_list])

        return jsonify({'success': True, 'transcript': transcript_text})

    except Exception as e:
        return jsonify({'success': False, 'error': f'Could not fetch transcript: {str(e)}'}), 500

@app.route('/api/update_video_type', methods=['POST'])
def update_video_type():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    video_id = data.get('video_id')
    video_type = data.get('video_type')

    if not video_id or not video_type:
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400

    try:
        conn = sqlite3.connect('database/piano_jazz_videos.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE videos SET video_type = ? WHERE id = ?', (video_type, video_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)