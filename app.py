from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import random
import os
from flask_socketio import SocketIO
import redis

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key')  # Replace with a strong secret key
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

# Redis configuration
redis_url = os.environ.get('REDIS_URL')
if not redis_url:
    raise ValueError("REDIS_URL environment variable not set.")

redis_client = redis.from_url(redis_url)

# Admin credentials (use environment variables or a more secure method in production)
ADMIN_NAME = os.environ.get('ADMIN_NAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'password')

def load_bingo_items(filename='bingo_items.txt'):
    try:
        with open(filename, "r") as file:
            lines = [line.strip() for line in file.readlines() if line.strip()]
        return lines
    except FileNotFoundError:
        return []

@app.route('/')
def index():
    bingo_items = load_bingo_items()
    if len(bingo_items) < 25:
        return "Not enough items to create a bingo card. Please add more items to the text file."
    random_items = random.sample(bingo_items, 25)
    random_items[12] = "Free Space"
    return render_template('index.html', card=random_items)

@socketio.on('bingo')
def handle_bingo_event(data):
    player_name = data.get('name')
    message = data.get('message')
    if player_name and message:
        try:
            redis_client.rpush('bingo_queue', f'{player_name}|{message}')
            print(f"Added to Redis queue: {player_name} - {message}")
        except Exception as e:
            print(f"Error adding bingo data to Redis: {e}")

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('admin_manage'))

    if request.method == 'POST':
        player_name = request.form.get('player_name')
        if player_name == ADMIN_NAME:
            return redirect(url_for('admin_password'))
        else:
            return "Invalid admin name", 403

    return render_template('admin_login.html')

@app.route('/admin/password', methods=['GET', 'POST'])
def admin_password():
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('admin_manage'))

    if request.method == 'POST':
        admin_password = request.form.get('admin_password')
        if admin_password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_manage'))
        else:
            return "Invalid password", 403

    return render_template('admin_password.html')

@app.route('/admin/manage', methods=['GET', 'POST'])
def admin_manage():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        if 'upload' in request.files:
            file = request.files['upload']
            if file.filename.endswith('.txt'):
                file.save('bingo_items.txt')
                return redirect(url_for('admin_manage'))
            else:
                return "Invalid file type", 400

    return render_template('admin_manage.html', items=load_bingo_items())

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))