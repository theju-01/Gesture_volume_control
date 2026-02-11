import cv2
import mediapipe as mp
import numpy as np
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
 
# Initialize MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands()
mp_draw = mp.solutions.drawing_utils
 
# Audio control setup
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume_ctrl = cast(interface, POINTER(IAudioEndpointVolume))
vol_range = volume_ctrl.GetVolumeRange()
min_vol, max_vol = vol_range[0], vol_range[1]
 
# Start webcam
cap = cv2.VideoCapture(0)
 
while True:
    success, img = cap.read()
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)
 
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            lm_list = []
            for id, lm in enumerate(hand_landmarks.landmark):
                h, w, _ = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append((cx, cy))
 
            if lm_list:
                x1, y1 = lm_list[4]   # Thumb tip
                x2, y2 = lm_list[8]   # Index tip
                distance = np.hypot(x2 - x1, y2 - y1)
 
                # Map distance to volume
                vol = np.interp(distance, [30, 200], [min_vol, max_vol])
                volume_ctrl.SetMasterVolumeLevel(vol, None)
 
                # Draw feedback
                cv2.circle(img, (x1, y1), 10, (255, 0, 0), -1)
                cv2.circle(img, (x2, y2), 10, (255, 0, 0), -1)
                cv2.line(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
 
    cv2.imshow("Gesture Volume Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
 
cap.release()
cv2.destroyAllWindows()
# Map distance to volume
vol = np.interp(distance, [30, 200], [min_vol, max_vol])
volume_ctrl.SetMasterVolumeLevel(vol, None)
 
# Convert volume to percentage for display
vol_percent = np.interp(distance, [30, 200], [0, 100])
 
# Draw feedback (circles + line)
cv2.circle(img, (x1, y1), 10, (255, 0, 0), -1)
cv2.circle(img, (x2, y2), 10, (255, 0, 0), -1)
cv2.line(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
 
# Draw volume bar
cv2.rectangle(img, (50, 150), (85, 400), (0, 255, 0), 3)  # Outline
bar_height = int(np.interp(vol_percent, [0, 100], [400, 150]))
cv2.rectangle(img, (50, bar_height), (85, 400), (0, 255, 0), -1)  # Fill
 
# Show percentage text
cv2.putText(img, f'{int(vol_percent)} %', (40, 450),
            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
import cv2
import mediapipe as mp
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
 
# Setup MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands()
mp_draw = mp.solutions.drawing_utils
 
# Setup audio control
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume_ctrl = cast(interface, POINTER(IAudioEndpointVolume))
 
# Webcam
cap = cv2.VideoCapture(0)
 
# Debounce variables
open_palm_counter = 0
debounce_threshold = 15  # frames required for stable detection
is_muted = False
 
def is_open_palm(lm_list):
    """Check if all fingers are extended (simple heuristic)."""
    # Thumb tip (4), Index tip (8), Middle tip (12), Ring tip (16), Pinky tip (20)
    finger_tips = [4, 8, 12, 16, 20]
    finger_knuckles = [2, 6, 10, 14, 18]
 
    extended = []
    for tip, knuckle in zip(finger_tips, finger_knuckles):
        extended.append(lm_list[tip][1] < lm_list[knuckle][1])  # y smaller = higher on screen
 
    return all(extended)
 
while True:
    success, img = cap.read()
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)
 
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            lm_list = []
            h, w, _ = img.shape
            for id, lm in enumerate(hand_landmarks.landmark):
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append((cx, cy))
 
            if lm_list:
                if is_open_palm(lm_list):
                    open_palm_counter += 1
                else:
                    open_palm_counter = 0
 
                # Trigger mute/unmute only if stable for threshold frames
                if open_palm_counter >= debounce_threshold:
                    is_muted = not is_muted
                    volume_ctrl.SetMute(is_muted, None)
                    print("Mute toggled:", is_muted)
                    open_palm_counter = 0  # reset after toggle
 
            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)
 
    cv2.imshow("Gesture Volume Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
 
cap.release()
cv2.destroyAllWindows()

import cv2
import mediapipe as mp
 
# Initialize webcam
cap = cv2.VideoCapture(0)
 
# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands()
mp_draw = mp.solutions.drawing_utils
 
while True:
    success, frame = cap.read()
    if not success:
        break
 
    # Convert to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)
 
    # Draw landmarks
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
 
    cv2.imshow("Hand Detection", frame)
 
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
 
cap.release()
cv2.destroyAllWindows()
 
 
 
 
 
