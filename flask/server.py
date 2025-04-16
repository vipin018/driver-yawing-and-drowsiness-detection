import cv2
import numpy as np
from scipy.spatial import distance
from flask import Flask, render_template, Response, jsonify

app = Flask(__name__)

# Load pre-trained face and eye detectors from OpenCV (Haar cascades)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
mouth_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')


# Thresholds
EYE_AR_THRESH = 0.25
EYE_AR_CONSEC_FRAMES = 20
MOUTH_AR_THRESH = 0.6

# Counters
eye_counter = 0
buzzer_triggered = False

# Function to calculate EAR (Eye Aspect Ratio) based on bounding box
def eye_aspect_ratio(eye_box):
    # Calculate the EAR from the bounding box (width / height)
    (x, y, w, h) = eye_box
    ear = h / float(w)  # Aspect ratio as height to width
    return ear

# Function to calculate MAR (Mouth Aspect Ratio)
def mouth_aspect_ratio(mouth_box):
    # Rough estimation: calculate MAR using the height/width ratio of the bounding box
    (x, y, w, h) = mouth_box
    mar = h / float(w)  # Aspect ratio as height to width
    return mar

# Initialize the webcam
# camera = cv2.VideoCapture("http://192.168.174.109:4747/video")  # 0 for local webcam, change to appropriate device if needed
camera = cv2.VideoCapture(0)  # 0 for local webcam, change to appropriate device if needed

def generate_frames():
    global eye_counter, buzzer_triggered
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            
            for (x, y, w, h) in faces:
                face_roi = gray[y:y+h, x:x+w]  # Region of interest (ROI) for face
                
                # Detect eyes within the face ROI
                eyes = eye_cascade.detectMultiScale(face_roi)
                for (ex, ey, ew, eh) in eyes:
                    left_eye_box = (ex, ey, ew, eh)
                    # Calculate EAR (Eye Aspect Ratio)
                    ear = eye_aspect_ratio(left_eye_box)
                    mar = 0  # For now, no mouth detection for MAR

                    # Draw bounding boxes and text for eyes
                    cv2.rectangle(frame, (x + ex, y + ey), (x + ex + ew, y + ey + eh), (0, 255, 0), 2)
                    if ear < EYE_AR_THRESH:
                        eye_counter += 1
                        if eye_counter >= EYE_AR_CONSEC_FRAMES:
                            buzzer_triggered = True
                            cv2.putText(frame, "DROWSINESS ALERT!", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    else:
                        eye_counter = 0  # Reset counter if eyes are open

                # Detect mouth within the face ROI
                mouths = mouth_cascade.detectMultiScale(face_roi)
                for (mx, my, mw, mh) in mouths:
                    mouth_box = (mx, my, mw, mh)
                    mar = mouth_aspect_ratio(mouth_box)

                    # Draw bounding box for mouth
                    cv2.rectangle(frame, (x + mx, y + my), (x + mx + mw, y + my + mh), (0, 0, 255), 2)

                    # Yawning Detection
                    if mar > MOUTH_AR_THRESH:
                        buzzer_triggered = True
                        cv2.putText(frame, "YAWNING ALERT!", (30, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # Encode frame for streaming
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/trigger_buzzer', methods=['POST'])
def trigger_buzzer():
    global buzzer_triggered
    if buzzer_triggered:
        print("Buzzer Triggered: Drowsiness/Yawning Detected")
        buzzer_triggered = False
        return jsonify({"status": "Buzzer Activated"})
    return jsonify({"status": "No Drowsiness Detected"})

@app.route('/get_buzzer_status')
def get_buzzer_status():
    global buzzer_triggered
    return "1" if buzzer_triggered else "0"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
