import socketio
import asyncio
import cv2
import base64
import subprocess
import datetime

socket = socketio.AsyncClient()
server = "http://localhost:5000"
botName = "Stream Bot"
botIcon = "data:image/png;base64,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"

@socket.event
async def connect():
	print('Connected')

@socket.event
async def message(data):
	if data['message'].startswith('https://'):
		url = data['message']
		room = data["room"]
		asyncio.create_task(stream_video(room, url))

@socket.event
async def disconnect():
	print('disconnected from server')
	await socket.disconnect()

@socket.event
def connect_error(message):
	print(message)


async def stream_video(room, url):
	await socket.emit('event', { 'event': 'start_video', 'room': room })
	
	fps = 20
	cap = cv2.VideoCapture(url)
	cap.set(cv2.CAP_PROP_FPS, fps)
	# fps = round(cap.get(cv2.CAP_PROP_FPS))

	audioSec = 0

	while True:
		cmd_audio = ["ffmpeg", "-i", url, '-vn', '-ss', str(datetime.timedelta(seconds=audioSec)),
					'-to', str(datetime.timedelta(seconds=audioSec+1)), '-f', 's16le', '-c:a', 'pcm_s16le',
					"-ac", "2", "-sample_rate","48000", '-ar','48000', "-acodec","libmp3lame", "pipe:1"]

		proc = subprocess.Popen(cmd_audio, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
		stdout, stderr = proc.communicate()
		audioSec+=1
		if proc.returncode == 0:
			await socket.emit('segment', { 'room': room, 'type': 'audio', 'stream': stdout})

			for i in range(fps):
				ret, frame = cap.read()
				if not ret: break
				_, img_bytes = cv2.imencode(".jpg", frame)
				img_base64 = base64.b64encode(img_bytes).decode('utf-8')
				img_data_url = f"data:image/jpeg;base64,{img_base64}"

				await socket.emit('segment', { 'room': room, 'type': 'video', 'stream': img_data_url})

				print("Streaming video...", end="\r")
				await asyncio.sleep(1/fps)

	cap.release()


async def main():
	room = input("Room: ")
	try:
		await socket.connect(server + f"?username={botName}&room={room}", headers={'icon': botIcon})
	except socketio.exceptions.ConnectionError:
		pass

	await socket.wait()
	

if __name__ == '__main__':
	asyncio.run(main())
