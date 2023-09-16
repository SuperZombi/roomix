from flask import Flask, render_template, request, redirect, abort
from flask_cors import CORS
from flask_socketio import SocketIO, emit, disconnect, ConnectionRefusedError
import hashlib
import time
import re
import json

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
CORS(app)
socketio = SocketIO(app)


class User():
	def __init__(self, name, id_, icon, is_bot):
		self.name = name
		self.id = id_
		self.isBot = is_bot
		self.icon = icon if icon else f"https://ui-avatars.com/api/?name={name}&length=1&color=fff&background=random&bold=true&format=svg&size=512"

	def receive_message(self, event, message):
		emit(event, message, namespace='/', broadcast=True, room=self.id)

	def __eq__(self, other):
		return self.id == other.id and self.name == other.name
	def __ne__(self, other):
		return not (self == other)

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
		self.users = [i for i in self.users if i != user]
		return len([i for i in self.users if not i.isBot]) == 0

	def disconnect_all(self):
		for user in self.users:
			disconnect(user.id)

	def get_user(self, atr, val):
		return next((user for user in self.users if getattr(user, atr) == val), None)

	def user_exists(self, username):
		return any(i.name == username for i in self.users)

	def send_message(self, event, message, ignore_user=None):
		for user in self.users:
			if ignore_user and user == ignore_user: continue
			if user.isBot and event != "message": continue
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
	username = request.args.get('user', '')
	room = get_room(room_id)
	if not room: return redirect('/')
	return render_template('room.html', room_id=room_id, username=username)


@socketio.on('connect')
def handle_join_room():
	username = request.args.get('username')
	if not username:
		raise ConnectionRefusedError('Unauthorized!')
	
	is_bot = False
	if request.referrer:
		pattern = r'/room/([^?]+)'
		match = re.search(pattern, request.referrer)
		room_id = match.group(1)
	else:
		room_id = request.args.get('room')
		is_bot = True

	room = get_room(room_id)
	if not room:
		raise ConnectionRefusedError('Room does not exist!')

	if room.user_exists(username):
		raise ConnectionRefusedError('User already exist!')

	icon = request.headers.get("icon")
	user = User(username, request.sid, icon=icon, is_bot=is_bot)
	room.add_user(user)
	room.send_message('join_room', {'user': serialize(user)}, ignore_user=user)
	if not is_bot:
		user.receive_message("connected", serialize(room.users))


@socketio.on('disconnect')
def handle_leave_room():
	global rooms
	if request.referrer:
		pattern = r'/room/([^?]+)'
		match = re.search(pattern, request.referrer)
		room_id = match.group(1)
	else:
		room_id = request.args.get('room')
	if room_id:
		room = get_room(room_id)
		if room:
			user = room.get_user("id", request.sid)
			if user:
				need_remove_room = room.remove_user(user)
				if need_remove_room:
					room.disconnect_all()
					rooms = [i for i in rooms if i.id != room.id]
				else:
					room.send_message('leave_room', {'user': serialize(user)})


@socketio.on('send_message')
def handle_send_message(data):
	room = get_room(data['room'])
	if not room: return
	user = room.get_user("id", request.sid)
	if not user: return

	message = data.get('message', '').strip()
	if message == '': return
	room.send_message('message', {'from_user': user.name, 'message': message, 'room': room.id})


@socketio.on('segment')
def segment(data):
	room = get_room(data['room'])
	if not room: return
	user = room.get_user("id", request.sid)
	if not user: return
	room.send_message('stream', {
		'from_user': user.name,
		'type': data['type'],
		'stream': data['stream']
	}, ignore_user=user)

@socketio.on('event')
def event(data):
	room = get_room(data['room'])
	if not room: return
	user = room.get_user("id", request.sid)
	if not user: return
	room.send_message(data['event'], {
		'from_user': user.name
	}, ignore_user=user)


if __name__ == '__main__':
	# socketio.run(app, debug=True)
	print("Running...")
	socketio.run(app, host='0.0.0.0', port=80)
