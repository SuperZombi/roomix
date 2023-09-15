from flask import Flask, render_template, request, jsonify, redirect, abort
from flask_socketio import SocketIO, join_room, leave_room, emit
import hashlib
import time
import re
import json

app = Flask(__name__)
socketio = SocketIO(app)


class User():
    def __init__(self, name, id_):
        self.name = name
        self.id = id_
        self.icon = f"https://ui-avatars.com/api/?name={name}&length=1&color=fff&background=random&bold=true&format=svg&size=512"

    def receive_message(self, event, message):
        emit(event, message, namespace='/', broadcast=True, room=self.id)

    def __repr__(self):
        return f"{self.name}"

    def json(self):
        ignore = ['id']
        return {key: value for key, value in vars(self).items() if key not in ignore}

class Room():
    def __init__(self, id_):
        self.id = id_
        self.users = []

    def add_user(self, user):
        self.users.append(user)

    def remove_user(self, user):
        self.users = [i for i in self.users if i.id != user.id]
        return len(self.users) == 0

    def get_user(self, atr, val):
        return next((user for user in self.users if getattr(user, atr) == val), None)

    def user_exists(self, username):
        return any(i.name == username for i in self.users)

    def send_message(self, event, message):
        for user in self.users:
            user.receive_message(event, message)

    def __repr__(self):
        return f"Room({self.id}: {self.users})"


rooms = []
def get_room(room_id):
    for room in rooms:
        if room.id == room_id:
            return room
    return False

def serialize(arr):
    return json.loads(json.dumps(arr, default=lambda cls: cls.json()))


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/new_room')
def new_room():
    username = request.args.get('user')
    if not username: abort(401)

    room_id = hashlib.md5(str(int(time.time())).encode('utf-8')).hexdigest()

    room = Room(room_id)
    rooms.append(room)
    return redirect(f'/room/{room_id}?user={username}')

@app.route('/room/<room_id>')
def room(room_id):
    username = request.args.get('user')
    if not username: abort(401)
    room = get_room(room_id)
    if not room: return redirect('/')
    return render_template('room.html', room_id=room_id, username=username)


@socketio.on('join_room')
def handle_join_room(data):
    username = data.get('username')
    if not username: return
    room = get_room(data['room'])
    if not room: return

    if not room.user_exists(username):
        user = User(username, request.sid)
        room.add_user(user)
        room.send_message('join_room', {'from_user': username})
    return serialize(room.users)

@socketio.on('disconnect')
def handle_leave_room():
    global rooms
    pattern = r'/room/([^?]+)'
    match = re.search(pattern, request.referrer)
    room = get_room(match.group(1))
    if room:
        user = room.get_user("id", request.sid)
        if user:
            need_remove_room = room.remove_user(user)
            if need_remove_room:
                rooms = [i for i in rooms if i.id != room.id]
            else:
                room.send_message('leave_room', {'from_user': user.name})


@socketio.on('send_message')
def handle_send_message(data):
    username = data.get('username')
    if not username: return
    room = get_room(data['room'])
    if not room: return

    message = data.get('message', '').strip()
    if message == '': return
    room.send_message('message', {'from_user': username, 'message': message})


@socketio.on('segment')
def segment(data):
    room = get_room(data['room'])
    if room:
        room.send_message('stream', {
            'from_user': data['username'],
            'type': data['type'],
            'stream': data['stream']
        })

@socketio.on('event')
def event(data):
    room = get_room(data['room'])
    if room:
        room.send_message(data['event'], {
            'from_user': data['username']
        })


if __name__ == '__main__':
    socketio.run(app, debug=True)
