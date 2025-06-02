import os
import sqlite3
from flask import Flask, request, render_template_string, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from random_words import RandomWords

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'py'}
DB_FILE = 'database.db'
rw = RandomWords()

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cur = conn.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    script TEXT,
    status TEXT,
    slug TEXT UNIQUE
)''')
conn.commit()

# HTML TEMPLATE
TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Bot Hosting</title>
    <style>
        body { font-family: sans-serif; padding: 40px; background: #f2f2f2; }
        h1 { color: #333; }
        table { width: 100%; background: #fff; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 10px; border: 1px solid #ccc; text-align: left; }
        .button { padding: 5px 10px; text-decoration: none; color: white; border-radius: 4px; margin-right: 4px; }
        .green { background: #28a745; }
        .red { background: #dc3545; }
        .orange { background: #fd7e14; }
        input[type="file"], input[type="text"] { padding: 5px; }
        form { margin-bottom: 20px; }
        button { padding: 5px 10px; }
    </style>
</head>
<body>
    <h1>Telegram Bot Hosting Panel</h1>
    <form method="POST" action="/upload" enctype="multipart/form-data">
        <input type="text" name="name" placeholder="Bot Name" required>
        <input type="file" name="script" accept=".py" required>
        <button type="submit">Upload Bot</button>
    </form>
    <table>
        <tr>
            <th>Name</th>
            <th>File</th>
            <th>Status</th>
            <th>Actions / Link</th>
        </tr>
        {% for bot in bots %}
        <tr>
            <td>{{ bot[1] }}</td>
            <td>{{ bot[2].split('/')[-1] }}</td>
            <td>{{ bot[3] }}</td>
            <td>
                {% if bot[3] == 'running' %}
                    <a class="button red" href="/stop/{{ bot[0] }}">Stop</a>
                {% else %}
                    <a class="button green" href="/start/{{ bot[0] }}">Start</a>
                {% endif %}
                <a class="button orange" href="/restart/{{ bot[0] }}">Restart</a>
                <a class="button red" href="/delete/{{ bot[0] }}" onclick="return confirm('Delete this bot?')">Delete</a>
                <br><br>
                {% if bot[4] %}
                    <input type="text" value="https://hosting-c451.onrender.com/access/{{ bot[4] }}" id="link-{{ bot[0] }}" readonly style="width:80%; padding:3px;">
                    <button onclick="copyLink({{ bot[0] }})">Copy</button>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>

    <script>
        function copyLink(id) {
            var copyText = document.getElementById("link-" + id);
            copyText.select();
            copyText.setSelectionRange(0, 99999);
            document.execCommand("copy");
            alert("Copied: " + copyText.value);
        }
    </script>
</body>
</html>
'''

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    cur.execute("SELECT * FROM bots")
    bots = cur.fetchall()
    return render_template_string(TEMPLATE, bots=bots)

@app.route('/upload', methods=['POST'])
def upload():
    name = request.form['name']
    file = request.files['script']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        slug = '-'.join(rw.random_words(count=3))
        cur.execute("INSERT INTO bots (name, script, status, slug) VALUES (?, ?, ?, ?)", (name, filepath, 'stopped', slug))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/start/<int:bot_id>')
def start(bot_id):
    cur.execute("UPDATE bots SET status='running' WHERE id=?", (bot_id,))
    conn.commit()
    return redirect(url_for('index'))

@app.route('/stop/<int:bot_id>')
def stop(bot_id):
    cur.execute("UPDATE bots SET status='stopped' WHERE id=?", (bot_id,))
    conn.commit()
    return redirect(url_for('index'))

@app.route('/restart/<int:bot_id>')
def restart(bot_id):
    cur.execute("UPDATE bots SET status='running' WHERE id=?", (bot_id,))
    conn.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:bot_id>')
def delete(bot_id):
    cur.execute("SELECT script FROM bots WHERE id=?", (bot_id,))
    row = cur.fetchone()
    if row:
        try:
            os.remove(row[0])
        except:
            pass
    cur.execute("DELETE FROM bots WHERE id=?", (bot_id,))
    conn.commit()
    return redirect(url_for('index'))

@app.route('/access/<slug>')
def access_slug(slug):
    cur.execute("SELECT script FROM bots WHERE slug=?", (slug,))
    row = cur.fetchone()
    if not row:
        return "Invalid link", 404
    filename = os.path.basename(row[0])
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
