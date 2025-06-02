import os
import time
import sqlite3
import subprocess
import threading
from flask import Flask, request, redirect, url_for, render_template_string, flash

# === AUTO-INSTALL REQUIREMENTS ===
if os.path.exists("requirements.txt"):
    os.system("pip install -r requirements.txt")

# === CONFIG ===
UPLOAD_FOLDER = 'bots'
DB_FILE = 'bots.db'
app = Flask(__name__)
app.secret_key = 'your-secret-key'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cur = conn.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    script TEXT,
    status TEXT
)''')
conn.commit()

running = {}  # bot_id: process
logs = {}     # bot_id: log string

# === HTML UI TEMPLATE ===
TEMPLATE = '''
<!doctype html>
<html>
<head>
<title>📡 Python Bot Hosting Panel</title>
<style>
body { font-family: sans-serif; background: #f8f8f8; margin: 30px; }
h2 { color: #333; }
form, table { margin-top: 20px; }
input[type="text"], input[type="file"] { padding: 5px; margin: 5px; }
input[type="submit"] { padding: 6px 12px; background: #28a745; color: white; border: none; border-radius: 4px; }
table { width: 100%; border-collapse: collapse; margin-top: 20px; }
th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
th { background: #eee; }
pre { background: #000; color: #0f0; padding: 5px; max-height: 200px; overflow-y: auto; }
a.button { padding: 4px 10px; margin-right: 4px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
a.button.red { background: #dc3545; }
a.button.green { background: #28a745; }
a.button.orange { background: #fd7e14; }
</style>
</head>
<body>
<h2>🤖 Bot Hosting Dashboard (Python, Flask, Termux Compatible)</h2>

{% with messages = get_flashed_messages() %}
  {% if messages %}
    <ul style="color: red;">
      {% for msg in messages %}
        <li>{{ msg }}</li>
      {% endfor %}
    </ul>
  {% endif %}
{% endwith %}

<form method="post" enctype="multipart/form-data" action="/upload">
  <input type="text" name="name" placeholder="Bot Name" required>
  <input type="file" name="script" required>
  <input type="submit" value="Upload Bot">
</form>

<table>
<tr><th>Name</th><th>Status</th><th>Actions</th><th>Live Logs</th></tr>
{% for bot in bots %}
<tr>
<td>{{ bot[1] }}</td>
<td>{{ bot[3] }}</td>
<td>
  {% if bot[3] == 'running' %}
    <a class="button red" href="/stop/{{ bot[0] }}">Stop</a>
  {% else %}
    <a class="button green" href="/start/{{ bot[0] }}">Start</a>
  {% endif %}
  <a class="button orange" href="/restart/{{ bot[0] }}">Restart</a>
  <a class="button red" href="/delete/{{ bot[0] }}" onclick="return confirm('Delete this bot?')">Delete</a>
</td>
<td><pre>{{ logs.get(bot[0], '') }}</pre></td>
</tr>
{% endfor %}
</table>
</body>
</html>
'''

# === BOT RUNNER ===
def run_bot(bot_id, script_path):
    def runner():
        try:
            proc = subprocess.Popen(
                ['python', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            running[bot_id] = proc
            update_status(bot_id, 'running')
            all_logs = ''
            for line in proc.stdout:
                all_logs += line
                logs[bot_id] = all_logs[-5000:]
            proc.wait()
        except Exception as e:
            logs[bot_id] = logs.get(bot_id, '') + f'\n[ERROR] {e}'
        update_status(bot_id, 'stopped')

    threading.Thread(target=runner, daemon=True).start()

def update_status(bot_id, status):
    cur.execute("UPDATE bots SET status=? WHERE id=?", (status, bot_id))
    conn.commit()

# === ROUTES ===
@app.route('/')
def index():
    cur.execute("SELECT * FROM bots")
    return render_template_string(TEMPLATE, bots=cur.fetchall(), logs=logs)

@app.route('/upload', methods=['POST'])
def upload():
    name = request.form['name']
    file = request.files['script']
    if not file.filename.endswith('.py'):
        flash('Only .py files are allowed')
        return redirect(url_for('index'))
    filename = f"{int(time.time())}_{file.filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    cur.execute("INSERT INTO bots (name, script, status) VALUES (?, ?, ?)", (name, filepath, 'stopped'))
    conn.commit()
    flash('Bot uploaded successfully!')
    return redirect(url_for('index'))

@app.route('/start/<int:bot_id>')
def start(bot_id):
    cur.execute("SELECT script FROM bots WHERE id=?", (bot_id,))
    row = cur.fetchone()
    if row:
        run_bot(bot_id, row[0])
        flash('Bot started.')
    return redirect(url_for('index'))

@app.route('/stop/<int:bot_id>')
def stop(bot_id):
    proc = running.get(bot_id)
    if proc:
        proc.terminate()
        update_status(bot_id, 'stopped')
        running.pop(bot_id, None)
        flash('Bot stopped.')
    else:
        flash('Bot is not running.')
    return redirect(url_for('index'))

@app.route('/restart/<int:bot_id>')
def restart(bot_id):
    stop(bot_id)
    time.sleep(1)
    start(bot_id)
    flash('Bot restarted.')
    return redirect(url_for('index'))

@app.route('/delete/<int:bot_id>')
def delete(bot_id):
    proc = running.get(bot_id)
    if proc:
        proc.terminate()
        running.pop(bot_id, None)
        logs.pop(bot_id, None)
    cur.execute("SELECT script FROM bots WHERE id=?", (bot_id,))
    row = cur.fetchone()
    if row and os.path.exists(row[0]):
        os.remove(row[0])
    cur.execute("DELETE FROM bots WHERE id=?", (bot_id,))
    conn.commit()
    flash('Bot deleted.')
    return redirect(url_for('index'))

# === START SERVER ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
