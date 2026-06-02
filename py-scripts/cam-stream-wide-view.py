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

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

camera = Picamera2()
config = camera.create_video_configuration(
    main={"size": (1200, 675)},
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
camera.start_recording(MJPEGEncoder(bitrate=10000000), FileOutput(output))

def generate_frames():
    while True:
        with output.condition:
            output.condition.wait()
            frame = output.frame
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
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)