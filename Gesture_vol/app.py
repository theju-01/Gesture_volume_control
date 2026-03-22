import cv2
import mediapipe as mp
import numpy as np
from flask import Flask, render_template, Response, jsonify, request
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import math
import time

# ================== DISTANCE → VOLUME FUNCTION ==================
def map_distance_to_volume(distance, min_dist, max_dist):
    distance = np.clip(distance, min_dist, max_dist)
    normalized = (distance - min_dist) / (max_dist - min_dist)
    return int(normalized * 100)


app = Flask(__name__)

# ================== SYSTEM VOLUME ==================
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(
    IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))
minVol, maxVol, _ = volume.GetVolumeRange()

# ================== MEDIAPIPE ==================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

# ================== GLOBAL STATE ==================
current_gesture = "None"
gesture_emoji = ""
volume_percent = 0
last_volume_percent = 0
pinch_distance = 0
hand_count = 0
fps = 0
prev_time = 0

manual_min_pinch = 20
manual_max_pinch = 240
volume_step_percent = 5

# NEW FEATURE
lock_mode = False
fist_start_time = None


def fingers_up(hand_landmarks, hand_label):
    tips = [8, 12, 16, 20]
    fingers = []

    if hand_label == "Right":
        fingers.append(1 if hand_landmarks.landmark[4].x <
                       hand_landmarks.landmark[3].x else 0)
    else:
        fingers.append(1 if hand_landmarks.landmark[4].x >
                       hand_landmarks.landmark[3].x else 0)

    for tip in tips:
        fingers.append(1 if hand_landmarks.landmark[tip].y <
                       hand_landmarks.landmark[tip - 2].y else 0)

    return fingers


def generate_frames():
    global current_gesture, gesture_emoji
    global volume_percent, pinch_distance
    global hand_count, fps, prev_time
    global last_volume_percent
    global manual_min_pinch, manual_max_pinch, volume_step_percent
    global lock_mode, fist_start_time

    PINCH_THRESHOLD = 40
    SMOOTH_FACTOR = 0.2

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        force_exact = False

        if results.multi_hand_landmarks:

            hand_count = len(results.multi_hand_landmarks)

            # ================== CLOSEST HAND PRIORITY ==================
            chosen_hand = None
            chosen_label = None
            closest_score = 0

            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):

                lm = hand_landmarks.landmark
                x1, y1 = lm[0].x, lm[0].y
                x2, y2 = lm[12].x, lm[12].y

                dist = math.hypot(x2 - x1, y2 - y1)

                if dist > closest_score:
                    closest_score = dist
                    chosen_hand = hand_landmarks
                    chosen_label = results.multi_handedness[idx].classification[0].label

            # Draw all hands
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS
                )

            lm = chosen_hand.landmark
            fingers = fingers_up(chosen_hand, chosen_label)

            x1, y1 = int(lm[4].x * w), int(lm[4].y * h)
            x2, y2 = int(lm[8].x * w), int(lm[8].y * h)

            cv2.line(frame, (x1, y1), (x2, y2), (255, 255, 0), 3)

            pinch_distance = int(math.hypot(x2 - x1, y2 - y1))

            raw_volume = map_distance_to_volume(
                pinch_distance,
                manual_min_pinch,
                manual_max_pinch
            )

            raw_volume = max(0, min(100, raw_volume))

            raw_volume = int(
                round(raw_volume / volume_step_percent)
                * volume_step_percent
            )

            # ================== GESTURES ==================
            current_gesture = "None"
            gesture_emoji = ""

            if fingers == [0, 0, 0, 0, 0]:

                current_gesture = "Fist"
                gesture_emoji = "✊"

                if fist_start_time is None:
                    fist_start_time = time.time()

                hold_time = time.time() - fist_start_time

                if hold_time > 2:
                    lock_mode = not lock_mode
                    fist_start_time = None

                raw_volume = 0
                force_exact = True

            else:
                fist_start_time = None

                if fingers == [1, 1, 1, 1, 1]:
                    current_gesture = "Open Palm"
                    gesture_emoji = "🖐"
                    raw_volume = 100
                    force_exact = True

                elif pinch_distance < PINCH_THRESHOLD and fingers[1] == 1:
                    current_gesture = "Pinch"
                    gesture_emoji = "🤏"

                elif fingers == [1, 0, 0, 0, 0] and pinch_distance > 80:
                    current_gesture = "Thumbs Up"
                    gesture_emoji = "👍"
                    raw_volume = 50
                    force_exact = True

                elif fingers == [0, 1, 1, 0, 0]:
                    current_gesture = "Peace"
                    gesture_emoji = "✌"

                elif fingers == [0, 1, 1, 1, 0]:
                    current_gesture = "Three"

            # ================== SMOOTHING ==================
            if force_exact:
                volume_percent = raw_volume
            else:
                volume_percent = int(
                    last_volume_percent +
                    (raw_volume - last_volume_percent) * SMOOTH_FACTOR
                )

            last_volume_percent = volume_percent

            if not lock_mode:
                vol = np.interp(volume_percent, [0, 100], [minVol, maxVol])
                volume.SetMasterVolumeLevel(vol, None)

        else:
            hand_count = 0

        current_time = time.time()
        fps = 1 / (current_time - prev_time) if prev_time else 0
        prev_time = current_time

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' +
               frame + b'\r\n')


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/data')
def data():

    latency_ms = int(1000 / fps) if fps > 0 else 0

    if pinch_distance > 80:
        distance_state = "Open"
    elif pinch_distance < 20:
        distance_state = "Closed"
    else:
        distance_state = "Pinch"

    if hand_count == 0:
        detection_status = "No Hand Detected"
        accuracy = 0
    else:
        detection_status = "Hand Detected"
        accuracy = min(100, int((fps / 30) * 100))

    return jsonify({
        "fps": int(fps),
        "latency": latency_ms,
        "hands": hand_count,
        "gesture": current_gesture,
        "emoji": gesture_emoji,
        "pinch": pinch_distance,
        "volume": volume_percent,
        "distance_state": distance_state,
        "detection_status": detection_status,
        "accuracy": accuracy,
        "lock_mode": lock_mode
    })


@app.route('/update_calibration', methods=['POST'])
def update_calibration():
    global manual_min_pinch, manual_max_pinch, volume_step_percent
    data = request.json
    manual_min_pinch = int(data['min'])
    manual_max_pinch = int(data['max'])
    volume_step_percent = int(data['step'])
    return jsonify({"status": "updated"})


if __name__ == "__main__":
    app.run(debug=True)
    