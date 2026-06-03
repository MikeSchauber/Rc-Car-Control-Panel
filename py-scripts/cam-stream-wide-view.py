import io
from flask import Flask, Response
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
import threading

app = Flask(__name__)

class StreamOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()
        self.new_frame = False

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.new_frame = True
            self.condition.notify_all()

camera = Picamera2()
config = camera.create_video_configuration(
    main={"size": (854, 480)},
    controls={
        "FrameRate": 30,
        "AwbEnable": True,
        "AeEnable": True,
    },
    buffer_count=4
)
config["sensor"] = {"output_size": camera.sensor_resolution, "bit_depth": 10}
camera.configure(config)

output = StreamOutput()
camera.start_recording(MJPEGEncoder(bitrate=6000000), FileOutput(output))

def generate_frames():
    while True:
        with output.condition:
            # Warte max 100ms auf neues Frame, sonst skip
            output.condition.wait(timeout=0.1)
            if not output.new_frame or output.frame is None:
                continue
            frame = output.frame
            output.new_frame = False  # Als gelesen markieren
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    response = Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)