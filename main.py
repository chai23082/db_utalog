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
    conn.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, title TEXT NOT NULL, artist TEXT, 
            key_setting INTEGER, excitement INTEGER, 
            score REAL, model_type TEXT, genre TEXT
        )
    ''')
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
        query = "SELECT * FROM records WHERE 1=1"
        params = []
        if search_word:
            query += " AND (title LIKE ? OR artist LIKE ?)"
            params.extend([f'%{search_word}%', f'%{search_word}%'])
        if target_exc:
            query += " AND excitement = ?"
            params.append(target_exc)
        if target_model:
            query += " AND model_type = ?"
            params.append(target_model)
        
        query += " ORDER BY date DESC, id DESC"
        records = conn.execute(query, params).fetchall()

    # ランキング集計
    count_rank, high_score_rank, avg_score_rank = [], [], []
    artist_count_rank, artist_avg_rank = [], []

    if mode == 'ranking':
        # 曲別
        count_rank = conn.execute('SELECT title, artist, COUNT(*) as val FROM records GROUP BY title, artist ORDER BY val DESC LIMIT 10').fetchall()
        high_score_rank = conn.execute('SELECT title, artist, MAX(score) as val FROM records GROUP BY title, artist ORDER BY val DESC LIMIT 10').fetchall()
        avg_score_rank = conn.execute('SELECT title, artist, AVG(score) as val FROM records GROUP BY title, artist ORDER BY val DESC LIMIT 10').fetchall()
        # 歌手別
        artist_count_rank = conn.execute('SELECT artist, COUNT(*) as val FROM records WHERE artist != "" GROUP BY artist ORDER BY val DESC LIMIT 10').fetchall()
        artist_avg_rank = conn.execute('SELECT artist, AVG(score) as val FROM records WHERE artist != "" GROUP BY artist ORDER BY val DESC LIMIT 10').fetchall()

    conn.close()
    return render_template('index.html', mode=mode, records=records, 
                           count_rank=count_rank, high_score_rank=high_score_rank, 
                           avg_score_rank=avg_score_rank, artist_count_rank=artist_count_rank,
                           artist_avg_rank=artist_avg_rank,
                           search_word=search_word, target_exc=target_exc, target_model=target_model)

@app.route('/add', methods=['POST'])
def add():
    title = request.form.get('title')
    if not title: return redirect(url_for('index'))
    data = (request.form.get('date') or datetime.now().strftime('%Y-%m-%d'),
            title, request.form.get('artist'), request.form.get('key_setting') or 0,
            request.form.get('excitement') or 3, request.form.get('score') or 0,
            request.form.get('model_type'), request.form.get('genre'))
    conn = get_db_connection()
    conn.execute('INSERT INTO records (date, title, artist, key_setting, excitement, score, model_type, genre) VALUES (?,?,?,?,?,?,?,?)', data)
    conn.commit()
    conn.close()
    return redirect(url_for('index', mode='history'))

@app.route('/edit/<int:id>')
def edit(id):
    conn = get_db_connection()
    record = conn.execute('SELECT * FROM records WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('edit.html', record=record)

@app.route('/update/<int:id>', methods=['POST'])
def update(id):
    data = (request.form.get('date'), request.form.get('title'), request.form.get('artist'),
            request.form.get('key_setting'), request.form.get('excitement'),
            request.form.get('score'), request.form.get('model_type'), request.form.get('genre'), id)
    conn = get_db_connection()
    conn.execute('UPDATE records SET date=?, title=?, artist=?, key_setting=?, excitement=?, score=?, model_type=?, genre=? WHERE id=?', data)
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