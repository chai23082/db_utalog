from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('karaoke.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # 1. 歌手テーブル
    conn.execute('CREATE TABLE IF NOT EXISTS artists (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)')
    # 2. 曲テーブル (歌手テーブルと紐付け)
    conn.execute('CREATE TABLE IF NOT EXISTS songs (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, artist_id INTEGER, genre TEXT, UNIQUE(title, artist_id))')
    # 3. 歌唱記録テーブル (曲テーブルと紐付け)
    conn.execute('''CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        song_id INTEGER, date TEXT, score REAL, 
        key_setting INTEGER, excitement INTEGER, model_type TEXT)''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    mode = request.args.get('mode', 'history')
    search_word = request.args.get('search', '')
    target_exc = request.args.get('target_excitement', '')
    target_model = request.args.get('target_model', '')

    conn = get_db_connection()
    records = []
    
    if mode == 'history':
        
        
        query = '''
            SELECT r.id, r.date, r.score, r.key_setting, r.excitement, r.model_type, 
                   s.title, a.name as artist, s.genre 
            FROM records r
            JOIN songs s ON r.song_id = s.id
            JOIN artists a ON s.artist_id = a.id
            WHERE 1=1
        '''
        params = []
        if search_word:
            query += " AND (s.title LIKE ? OR a.name LIKE ?)"
            params.extend([f'%{search_word}%', f'%{search_word}%'])
        if target_exc:
            query += " AND r.excitement = ?"
            params.append(target_exc)
        if target_model:
            query += " AND r.model_type = ?"
            params.append(target_model)
        
        query += " ORDER BY r.date DESC, r.id DESC"
        records = conn.execute(query, params).fetchall()

    # ランキング集計
    count_rank, high_score_rank, avg_score_rank = [], [], []
    artist_count_rank, artist_avg_rank = [], []

    if mode == 'ranking':
        # 曲別集計
        count_rank = conn.execute('SELECT s.title, a.name as artist, COUNT(*) as val FROM records r JOIN songs s ON r.song_id = s.id JOIN artists a ON s.artist_id = a.id GROUP BY s.id ORDER BY val DESC LIMIT 10').fetchall()
        high_score_rank = conn.execute('SELECT s.title, a.name as artist, MAX(r.score) as val FROM records r JOIN songs s ON r.song_id = s.id JOIN artists a ON s.artist_id = a.id GROUP BY s.id ORDER BY val DESC LIMIT 10').fetchall()
        # 歌手別集計
        artist_count_rank = conn.execute('SELECT a.name as artist, COUNT(*) as val FROM records r JOIN songs s ON r.song_id = s.id JOIN artists a ON s.artist_id = a.id GROUP BY a.id ORDER BY val DESC LIMIT 10').fetchall()
        artist_avg_rank = conn.execute('SELECT a.name as artist, AVG(r.score) as val FROM records r JOIN songs s ON r.song_id = s.id JOIN artists a ON s.artist_id = a.id GROUP BY a.id ORDER BY val DESC LIMIT 10').fetchall()

    conn.close()
    return render_template('index.html', mode=mode, records=records, 
                           count_rank=count_rank, high_score_rank=high_score_rank, 
                           artist_count_rank=artist_count_rank, artist_avg_rank=artist_avg_rank,
                           search_word=search_word, target_exc=target_exc, target_model=target_model)

@app.route('/add', methods=['POST'])
def add():
    title = request.form.get('title')
    artist_name = request.form.get('artist') or "不明"
    if not title: return redirect(url_for('index'))

    conn = get_db_connection()
    # 1. 歌手を登録/ID取得
    conn.execute('INSERT OR IGNORE INTO artists (name) VALUES (?)', (artist_name,))
    artist_id = conn.execute('SELECT id FROM artists WHERE name = ?', (artist_name,)).fetchone()['id']
    
    # 2. 曲を登録/ID取得
    conn.execute('INSERT OR IGNORE INTO songs (title, artist_id, genre) VALUES (?, ?, ?)', (title, artist_id, request.form.get('genre')))
    song_id = conn.execute('SELECT id FROM songs WHERE title = ? AND artist_id = ?', (title, artist_id)).fetchone()['id']

    # 3. 歌唱記録を保存
    data = (song_id, request.form.get('date') or datetime.now().strftime('%Y-%m-%d'),
            request.form.get('score') or 0, request.form.get('key_setting') or 0,
            request.form.get('excitement') or 3, request.form.get('model_type'))
    conn.execute('INSERT INTO records (song_id, date, score, key_setting, excitement, model_type) VALUES (?,?,?,?,?,?)', data)
    conn.commit()
    conn.close()
    return redirect(url_for('index', mode='history'))

@app.route('/edit/<int:id>')
def edit(id):
    conn = get_db_connection()
   
    record = conn.execute('''
        SELECT r.*, s.title, a.name as artist, s.genre 
        FROM records r 
        JOIN songs s ON r.song_id = s.id 
        JOIN artists a ON s.artist_id = a.id 
        WHERE r.id = ?''', (id,)).fetchone()
    conn.close()
    return render_template('edit.html', record=record)

@app.route('/update/<int:id>', methods=['POST'])
def update(id):
    
    data = (request.form.get('date'), request.form.get('score'), 
            request.form.get('key_setting'), request.form.get('excitement'), 
            request.form.get('model_type'), id)
    conn = get_db_connection()
    conn.execute('UPDATE records SET date=?, score=?, key_setting=?, excitement=?, model_type=? WHERE id=?', data)
    conn.commit()
    conn.close()
    return redirect(url_for('index', mode='history'))

@app.route('/delete/<int:id>')
def delete(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM records WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index', mode='history'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=8888)