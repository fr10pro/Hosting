import os import time import sqlite3 import subprocess import threading from flask import Flask, request, redirect, url_for, render_template_string, flash
 
# === AUTO-INSTALL REQUIREMENTS ===
 
if os.path.exists("requirements.txt"): os.system("pip install -r requirements.txt")
 
# === CONFIG ===
 
UPLOAD_FOLDER = 'bots' DB_FILE = 'bots.db' app = Flask(**name**) app.secret_key = 'your-secret-key'
 
os.makedirs(UPLOAD_FOLDER, exist_ok=True) conn = sqlite3.connect(DB_FILE, check_same_thread=False) cur = conn.cursor() cur.execute('''CREATE TABLE IF NOT EXISTS bots ( id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, script TEXT, status TEXT )''') conn.commit()
 
running = {}  # bot_id: process logs = {}     # bot_id: log string
 
# === HTML UI TEMPLATE ===
 
TEMPLATE = ''' 
       📡 Python Bot Hosting Panel            
## 🤖 Bot Hosting Dashboard (Python, Flask, Termux Compatible)
   
{% with messages = get_flashed_messages() %} {% if messages %} 
 {% for msg in messages %} 
- {{ msg }}
 {% endfor %} 

 {% endif %} {% endwith %}
                      
   
Name
Status
Actions
Live Logs
   {% for bot in bots %}   
   
{{ bot[1] }}
   
{{ bot[3] }}
   
     {% if bot[3] == 'running' %}       Stop     {% else %}       Start     {% endif %}     Restart     Delete   
   
{{ logs.get(bot[0], '') }}
   
   {% endfor %}   
      '''   
# === BOT RUNNER ===
 
def run_bot(bot_id, script_path): def runner(): try: proc = subprocess.Popen( ['python', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True ) running[bot_id] = proc update_status(bot_id, 'running') all_logs = '' for line in proc.stdout: all_logs += line logs[bot_id] = all_logs[-5000:] proc.wait() except Exception as e: logs[bot_id] = logs.get(bot_id, '') + f'\n[ERROR] {e}' update_status(bot_id, 'stopped')
 `threading.Thread(target=runner, daemon=True).start()   ` 
def update_status(bot_id, status): cur.execute("UPDATE bots SET status=? WHERE id=?", (status, bot_id)) conn.commit()
 
# === ROUTES ===
 
@app.route('/') def index(): cur.execute("SELECT * FROM bots") return render_template_string(TEMPLATE, bots=cur.fetchall(), logs=logs)
 
@app.route('/upload', methods=['POST']) def upload(): name = request.form['name'] file = request.files['script'] if not file.filename.endswith('.py'): flash('Only .py files are allowed') return redirect(url_for('index')) filename = f"{int(time.time())}_{file.filename}" filepath = os.path.join(UPLOAD_FOLDER, filename) file.save(filepath) cur.execute("INSERT INTO bots (name, script, status) VALUES (?, ?, ?)", (name, filepath, 'stopped')) conn.commit() flash('Bot uploaded successfully!') return redirect(url_for('index'))
 
@app.route('/start/int:bot_id') def start(bot_id): cur.execute("SELECT script FROM bots WHERE id=?", (bot_id,)) row = cur.fetchone() if row: run_bot(bot_id, row[0]) flash('Bot started.') return redirect(url_for('index'))
 
@app.route('/stop/int:bot_id') def stop(bot_id): proc = running.get(bot_id) if proc: proc.terminate() update_status(bot_id, 'stopped') running.pop(bot_id, None) flash('Bot stopped.') else: flash('Bot is not running.') return redirect(url_for('index'))
 
@app.route('/restart/int:bot_id') def restart(bot_id): stop(bot_id) time.sleep(1) start(bot_id) flash('Bot restarted.') return redirect(url_for('index'))
 
@app.route('/delete/int:bot_id') def delete(bot_id): proc = running.get(bot_id) if proc: proc.terminate() running.pop(bot_id, None) logs.pop(bot_id, None) cur.execute("SELECT script FROM bots WHERE id=?", (bot_id,)) row = cur.fetchone() if row and os.path.exists(row[0]): os.remove(row[0]) cur.execute("DELETE FROM bots WHERE id=?", (bot_id,)) conn.commit() flash('Bot deleted.') return redirect(url_for('index'))
 
# === START SERVER ===
 
if **name** == '**main**': app.run(host='0.0.0.0', port=5000)
