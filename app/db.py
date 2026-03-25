import sqlite3
from flask import g, current_app


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE_PATH'], timeout=10.0)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def ensure_category_columns():
    """Auto-migration: Add category/analysis_depth columns if they don't exist."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(videos)")
    videos_columns = [col[1] for col in cursor.fetchall()]
    if 'category' not in videos_columns:
        cursor.execute("ALTER TABLE videos ADD COLUMN category TEXT DEFAULT NULL")
        print("Added category column to videos table")

    cursor.execute("PRAGMA table_info(songs)")
    songs_columns = [col[1] for col in cursor.fetchall()]
    if 'category' not in songs_columns:
        cursor.execute("ALTER TABLE songs ADD COLUMN category TEXT DEFAULT NULL")
        print("Added category column to songs table")
    if 'analysis_depth' not in songs_columns:
        cursor.execute("ALTER TABLE songs ADD COLUMN analysis_depth TEXT DEFAULT NULL")
        print("Added analysis_depth column to songs table")

    db.commit()


def get_songs():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT
            s.id, s.video_id, s.song_title, s.composer, s.timestamp,
            s.part_number, s.total_parts, s.performer, s.original_artist,
            s.songwriters, s.composition_year, s.style, s.era,
            s.other_musicians, s.additional_info, s.video_title,
            s.video_url as url, s.video_description as description,
            s.published_at, s.album, s.record_label, s.recording_year,
            s.featured_artists, s.context_notes, s.analysis_depth,
            v.thumbnail_url, v.video_type,
            COALESCE(s.category, v.category) as category
        FROM songs s
        LEFT JOIN videos v ON s.video_id = v.id
        WHERE (s.deleted IS NULL OR s.deleted = 0)
        ORDER BY s.song_title ASC
    ''')
    return cursor.fetchall()
