from flask import Flask, render_template, request, jsonify
import random
import os
from flask_socketio import SocketIO
import redis

app = Flask(__name__)
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

# Redis configuration
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

flask_app_url = os.environ.get('FLASK_APP_URL', 'http://localhost:5001')

# Function to load bingo items from a text file
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
            # Push the bingo data to Redis list
            redis_client.rpush('bingo_queue', f'{player_name}|{message}')
            print(f"Added to Redis queue: {player_name} - {message}")
        except Exception as e:
            print(f"Error adding bingo data to Redis: {e}")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))