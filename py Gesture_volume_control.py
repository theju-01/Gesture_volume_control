import cv2
import mediapipe as mp
import numpy as np
import time
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# --- 1. CONFIGURATION & SETUP ---
w_cam, h_cam = 640, 480
sidebar_width = 200  # Width of the new UI sidebar
total_w = w_cam + sidebar_width

# Setup MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

# Custom Styles (Red Nodes, Green Lines)
landmark_style = mp_draw.DrawingSpec(color=(0, 0, 255), thickness=5, circle_radius=4)
connection_style = mp_draw.DrawingSpec(color=(0, 255, 0), thickness=3, circle_radius=2)

# Setup Audio (Windows)
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume_ctrl = cast(interface, POINTER(IAudioEndpointVolume))
vol_range = volume_ctrl.GetVolumeRange()
min_vol = vol_range[0]
max_vol = vol_range[1]

# State Variables
is_muted = False
mute_cooldown = 0  # To prevent accidental double-toggles
current_vol_per = 0

cap = cv2.VideoCapture(0)
cap.set(3, w_cam)
cap.set(4, h_cam)

print("System Ready. Pinch (Index+Thumb) for Volume. Touch (Pinky+Thumb) for Mute.")

while True:
    success, img = cap.read()
    if not success:
        break
    
    # 1. Prepare the Canvas (Camera + Sidebar)
    img = cv2.flip(img, 1)
    # Create a black background specifically for the UI sidebar
    background = np.zeros((h_cam, total_w, 3), dtype=np.uint8)
    # Paste the webcam feed on the left side
    background[0:h_cam, 0:w_cam] = img
    
    # Process Hand
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)
    
    lm_list = []
    hand_active = False

    if results.multi_hand_landmarks:
        hand_active = True
        for hand_landmarks in results.multi_hand_landmarks:
            # Draw Skeleton on the combined canvas
            # Note: We draw on 'background', so we don't need to offset X coords 
            # because the camera is at (0,0)
            mp_draw.draw_landmarks(background, hand_landmarks, mp_hands.HAND_CONNECTIONS, 
                                 landmark_style, connection_style)

            for id, lm in enumerate(hand_landmarks.landmark):
                h, w, _ = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append([id, cx, cy])

            if lm_list:
                # --- GESTURE 1: VOLUME (Index 8 + Thumb 4) ---
                x1, y1 = lm_list[4][1], lm_list[4][2] # Thumb
                x2, y2 = lm_list[8][1], lm_list[8][2] # Index
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                # Draw Blue Master Line
                cv2.line(background, (x1, y1), (x2, y2), (255, 0, 0), 3)

                length = np.hypot(x2 - x1, y2 - y1)
                
                # Only update volume if not muted (optional preference)
                vol = np.interp(length, [30, 200], [min_vol, max_vol])
                current_vol_per = np.interp(length, [30, 200], [0, 100])
                volume_ctrl.SetMasterVolumeLevel(vol, None)

                # --- GESTURE 2: MUTE (Pinky 20 + Thumb 4) ---
                x_pinky, y_pinky = lm_list[20][1], lm_list[20][2]
                mute_dist = np.hypot(x_pinky - x1, y_pinky - y1)

                # Check if touching (threshold < 30) and cooldown is over
                if mute_dist < 30 and time.time() - mute_cooldown > 1.0:
                    is_muted = not is_muted
                    volume_ctrl.SetMute(is_muted, None)
                    mute_cooldown = time.time()
                
                # Draw Pinky interaction line (Yellow if active)
                color_mute = (0, 255, 255) if mute_dist < 30 else (100, 100, 100)
                cv2.line(background, (x1, y1), (x_pinky, y_pinky), color_mute, 2)

    # --- DRAW DASHBOARD UI (Right Sidebar) ---
    ui_x_start = w_cam # Start drawing at pixel 640
    
    # 1. Status Header
    if hand_active:
        status_color = (0, 255, 0) # Green
        status_text = "CONNECTED"
    else:
        status_color = (0, 0, 255) # Red
        status_text = "SEARCHING..."
    
    cv2.putText(background, "STATUS:", (ui_x_start + 20, 50), cv2.FONT_HERSHEY_PLAIN, 1.5, (200, 200, 200), 2)
    cv2.putText(background, status_text, (ui_x_start + 20, 80), cv2.FONT_HERSHEY_COMPLEX, 1.2, status_color, 2)

    # 2. Volume Bar
    # Draw outline
    cv2.rectangle(background, (ui_x_start + 70, 150), (ui_x_start + 130, 400), (50, 50, 50), 3)
    # Calculate fill height
    bar_height = int(np.interp(current_vol_per, [0, 100], [400, 150]))
    # Fill based on volume (Cyan color)
    bar_color = (255, 255, 0) if not is_muted else (100, 100, 100) # Cyan normally, Grey if muted
    cv2.rectangle(background, (ui_x_start + 70, bar_height), (ui_x_start + 130, 400), bar_color, cv2.FILLED)
    
    # Volume Percentage Text
    cv2.putText(background, f'{int(current_vol_per)}%', (ui_x_start + 70, 430), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    # 3. Mute Alert
    if is_muted:
        cv2.rectangle(background, (ui_x_start + 20, 150), (ui_x_start + 180, 220), (0, 0, 255), cv2.FILLED)
        cv2.putText(background, "MUTED", (ui_x_start + 45, 200), cv2.FONT_HERSHEY_COMPLEX, 1.5, (255, 255, 255), 2)

    # 4. Legend
    cv2.putText(background, "Thumb+Index: Vol", (ui_x_start + 10, 460), cv2.FONT_HERSHEY_PLAIN, 1, (150, 150, 150), 1)
    cv2.putText(background, "Thumb+Pinky: Mute", (ui_x_start + 10, 475), cv2.FONT_HERSHEY_PLAIN, 1, (150, 150, 150), 1)

    cv2.imshow("Gesture Control Dashboard", background)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()