from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)

def get_videos():
    conn = sqlite3.connect('piano_jazz_videos.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM videos ORDER BY title ASC')
    videos = cursor.fetchall()
    conn.close()
    return videos

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

    videos = get_videos()

    # Categorize all videos
    categorized = []
    for v in videos:
        cat = categorize_video(v['title'], v['description'])
        categorized.append({
            'title': v['title'],
            'url': v['url'],
            'description': v['description'],
            'category': cat,
            'published_at': v['published_at']
        })

    # Search filter
    if search:
        search_lower = search.lower()
        categorized = [v for v in categorized if
                      search_lower in v['title'].lower() or
                      search_lower in v['description'].lower()]

    # Filter by category
    if category != 'all':
        categorized = [v for v in categorized if v['category'] == category]

    # Sort
    if sort == 'alpha':
        categorized.sort(key=lambda x: x['title'].lower())
    elif sort == 'theme':
        categorized.sort(key=lambda x: (x['category'], x['title'].lower()))
    elif sort == 'date':
        categorized.sort(key=lambda x: x['published_at'], reverse=True)

    # Get categories for filter
    all_categories = sorted(set(categorize_video(v['title'], v['description']) for v in videos))

    return render_template('index.html',
                         videos=categorized,
                         sort=sort,
                         category=category,
                         categories=all_categories,
                         search=search)

if __name__ == '__main__':
    app.run(debug=True, port=5000)