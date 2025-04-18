import cv2
import mediapipe as mp
import numpy as np
from scipy.spatial import distance
from flask import Flask, render_template, Response, jsonify

app = Flask(__name__)

# Use DroidCam IP feed
DROIDCAM_URL = "http://192.168.190.155:4747/video"

# MediaPipe setup
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, min_detection_confidence=0.5)

# Landmark indices
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]
MOUTH = [61, 291, 78, 308, 13, 14]

# Thresholds
EYE_AR_THRESH = 0.25
EYE_AR_CONSEC_FRAMES = 20
MOUTH_AR_THRESH = 0.6

eye_counter = 0

# Status flags
is_drowsy = False
is_yawning = False

def eye_aspect_ratio(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)

def mouth_aspect_ratio(mouth):
    A = distance.euclidean(mouth[2], mouth[4])
    B = distance.euclidean(mouth[1], mouth[5])
    C = distance.euclidean(mouth[0], mouth[3])
    return (A + B) / (2.0 * C)

def generate_frames():
    global eye_counter, is_drowsy, is_yawning
    cap = cv2.VideoCapture(DROIDCAM_URL)

    while True:
        success, frame = cap.read()
        if not success:
            continue

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(frame_rgb)

        is_drowsy = False
        is_yawning = False

        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                landmarks = np.array([(int(p.x * frame.shape[1]), int(p.y * frame.shape[0]))
                                      for p in face_landmarks.landmark])

                if max(LEFT_EYE + RIGHT_EYE + MOUTH) < len(landmarks):
                    left_eye = np.array([landmarks[i] for i in LEFT_EYE])
                    right_eye = np.array([landmarks[i] for i in RIGHT_EYE])
                    mouth = np.array([landmarks[i] for i in MOUTH])

                    for pt in left_eye:
                        cv2.circle(frame, pt, 2, (0, 255, 0), -1)
                    for pt in right_eye:
                        cv2.circle(frame, pt, 2, (0, 255, 0), -1)
                    for pt in mouth:
                        cv2.circle(frame, pt, 2, (0, 0, 255), -1)

                    left_ear = eye_aspect_ratio(left_eye)
                    right_ear = eye_aspect_ratio(right_eye)
                    ear = (left_ear + right_ear) / 2.0
                    mar = mouth_aspect_ratio(mouth)

                    if ear < EYE_AR_THRESH:
                        eye_counter += 1
                        if eye_counter >= EYE_AR_CONSEC_FRAMES:
                            is_drowsy = True
                            cv2.putText(frame, "DROWSINESS ALERT!", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                        (0, 0, 255), 2)
                    else:
                        eye_counter = 0

                    if mar > MOUTH_AR_THRESH:
                        is_yawning = True
                        cv2.putText(frame, "YAWNING ALERT!", (30, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                    (0, 0, 255), 2)

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

@app.route('/get_buzzer_status')
def get_buzzer_status():
    global is_drowsy, is_yawning
    if is_drowsy and is_yawning:
        return "both"
    elif is_drowsy:
        return "drowsy"
    elif is_yawning:
        return "yawn"
    else:
        return "normal"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
