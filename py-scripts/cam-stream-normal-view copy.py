import io
from flask import Flask, Response
from picamera2 import Picamera2
import cv2

app = Flask(__name__)

camera = Picamera2()
camera.configure(camera.create_video_configuration(
    main={"size": (920, 680)},  # kleinere Auflösung = schneller
    controls={"FrameRate": 30}
))
camera.start()

def generate_frames():
    while True:
        frame = camera.capture_array()

        # JPEG Qualität reduzieren = kleinere Datei = schneller
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    response = Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )
    # Caching deaktivieren
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)