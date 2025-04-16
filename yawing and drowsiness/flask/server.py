import cv2
import mediapipe as mp
import numpy as np
from scipy.spatial import distance
from flask import Flask, render_template, Response, jsonify

app = Flask(__name__)

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, min_detection_confidence=0.5)

# Indices for eye and mouth landmarks (based on MediaPipe's 468 points)
LEFT_EYE = [362, 385, 387, 263, 373, 380]  # Outer left eye
RIGHT_EYE = [33, 160, 158, 133, 153, 144]  # Outer right eye
MOUTH = [61, 291, 78, 308, 13, 14]  # Upper & lower lips

# Webcam
camera = cv2.VideoCapture(0)

# Thresholds
EYE_AR_THRESH = 0.25
EYE_AR_CONSEC_FRAMES = 20
MOUTH_AR_THRESH = 0.6

# Counters
eye_counter = 0
buzzer_triggered = False

# Function to calculate EAR (Eye Aspect Ratio)
def eye_aspect_ratio(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    ear = (A + B) / (2.0 * C)
    return ear

# Function to calculate MAR (Mouth Aspect Ratio)
def mouth_aspect_ratio(mouth):
    A = distance.euclidean(mouth[2], mouth[4])
    B = distance.euclidean(mouth[1], mouth[5])
    C = distance.euclidean(mouth[0], mouth[3])
    mar = (A + B) / (2.0 * C)
    return mar

def generate_frames():
    global eye_counter, buzzer_triggered
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(frame_rgb)

            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    landmarks = np.array([(int(p.x * frame.shape[1]), int(p.y * frame.shape[0])) 
                                          for p in face_landmarks.landmark])

                    # Ensure enough landmarks are detected before using them
                    if max(LEFT_EYE + RIGHT_EYE + MOUTH) < len(landmarks):
                        leftEye = np.array([landmarks[i] for i in LEFT_EYE])
                        rightEye = np.array([landmarks[i] for i in RIGHT_EYE])
                        mouth = np.array([landmarks[i] for i in MOUTH])

                        # Compute EAR & MAR
                        leftEAR = eye_aspect_ratio(leftEye)
                        rightEAR = eye_aspect_ratio(rightEye)
                        ear = (leftEAR + rightEAR) / 2.0
                        mar = mouth_aspect_ratio(mouth)

                        print(f"EAR: {ear:.2f}, MAR: {mar:.2f}")  # Debugging statement

                        # Draw landmarks
                        for point in leftEye:
                            cv2.circle(frame, tuple(point), 2, (0, 255, 0), -1)
                        for point in rightEye:
                            cv2.circle(frame, tuple(point), 2, (0, 255, 0), -1)
                        for point in mouth:
                            cv2.circle(frame, tuple(point), 2, (0, 0, 255), -1)

                        # Drowsiness Detection (Blinking)
                        if ear < EYE_AR_THRESH:
                            eye_counter += 1
                            if eye_counter >= EYE_AR_CONSEC_FRAMES:
                                buzzer_triggered = True
                                cv2.putText(frame, "DROWSINESS ALERT!", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        else:
                            eye_counter = 0  # Reset counter if eyes are open

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
