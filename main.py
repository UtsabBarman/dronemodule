import flask
import time
from flask import render_template, request
from drone.DoneVideo import VIDEO
from drone.TelloDrone import Tello
app = flask.Flask(__name__)
print('Click Here and see the video: http://127.0.0.1:9999/stream.mjpg\n\n\n')
fps = 25
interval = 1 / fps

tello = Tello()
video = VIDEO()

@app.route("/stream.mjpg")
def mjpg1():
        def generator():
            while True:
                time.sleep(interval)  # threading.condition is too shitty according to my test. no condition no lag.
                frame = video.jpeg_frame
                yield f'''--FRAME\r\nContent-Type: image/jpeg\r\nContent-Length: {len(frame)}\r\n\r\n'''.encode()
                yield frame

        r = flask.Response(response=generator(), status=200)
        r.headers.extend({'Age': 0, 'Content-Type': 'multipart/x-mixed-replace; boundary=FRAME',
                          'Pragma': 'no-cache', 'Cache-Control': 'no-cache, private', })
        return r

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/dronecontrol')
def dronecontrol():
    return render_template("dronecontrol.html")

@app.route('/command', methods=["POST"])
def command():
    if request.method == "POST":
        cmd = request.form.get("commands")
        tello.command(cmd)
        time.sleep(1)
    return render_template("dronecontrol.html")

if __name__ == '__main__':
    app.run('127.0.0.1', 9999)