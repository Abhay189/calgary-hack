from ultralytics import YOLO
import cv2
import math
import os
import boto3
from contextlib import closing
from pygame import mixer
import time
import threading

def synthesize_speech_async(text):
  
    # Initialize Polly client
    polly_client = boto3.client('polly', region_name='us-east-1', aws_access_key_id='aws_access_key_id', aws_secret_access_key='aws_secret_access_key')
    
    # Synthesize speech
    response = polly_client.synthesize_speech(VoiceId='Joanna', OutputFormat='mp3', Text=text)
    
    # Generate a unique filename using the current timestamp
    timestamp = int(time.time())
    filename = f"speech_{timestamp}.mp3"
    
    with closing(response['AudioStream']) as stream:
        with open(filename, "wb") as file:
            file.write(stream.read())

    # Initialize mixer only once or ensure it's not already initialized
    if not mixer.get_init():
        mixer.init()

    mixer.music.load(filename)
    mixer.music.play()

    # Wait for the audio to finish playing
    while mixer.music.get_busy():
        pass

    # Stop and unload the music
    mixer.music.stop()
    mixer.music.unload()  # If using Pygame 2.0.0 or newer, ensures the file is unloaded

    # Quit the mixer (optional, see note below)
    mixer.quit()

    # Delete the file after ensuring it's no longer in use
    try:
        os.remove(filename)
    except PermissionError as e:
        print(f"Error removing the file: {e}")


cap = cv2.VideoCapture(0)
cv2.namedWindow("Frame", cv2.WINDOW_NORMAL)
model = YOLO("yolo-Weights/yolov8n.pt")
classNames = ["person", "bicycle", "car", "bus", "traffic light"]
interested_classes = set(classNames)
min_confidence = 0.5
close_threshold = 0.3
close_status = {cls: False for cls in interested_classes}
class_position_status = {cls: "center" for cls in interested_classes}  # Track last known position

while True:
    success, img = cap.read()
    if not success:
        break
    frame_height, frame_width = img.shape[:2]
    frame_area = frame_width * frame_height
    results = model(img, stream=True)
    current_status = {cls: False for cls in interested_classes}
    detected_classes = set()

    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
            bbox_center = (x1 + x2) / 2
            position = "left" if bbox_center < frame_width / 3 else "right" if bbox_center > 2 * frame_width / 3 else "center"
            bbox_area = (x2 - x1) * (y2 - y1)
            area_ratio = bbox_area / frame_area
            confidence = math.ceil((box.conf[0]*100))/100

            # Check if box.cls has at least one element to avoid IndexError
            if confidence >= min_confidence and len(box.cls) > 0:
                cls_index = int(box.cls[0])  # Safely get the class index
                if cls_index < len(classNames) and classNames[cls_index] in interested_classes:
                    detected_classes.add(classNames[cls_index]) 
                    label = f"{classNames[cls_index]}: {confidence:.2f}" + (" - Too Close!" if area_ratio > close_threshold else "")
                    current_status[classNames[cls_index]] = area_ratio > close_threshold
                    class_position_status[classNames[cls_index]] = position  # Update the position

                    # Drawing the bounding box and label
                    cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 255), 3)
                    cv2.putText(img, label + f" - {position}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    # After processing all boxes
    for cls in interested_classes:
        # If class was detected in this frame
        if cls in detected_classes:
            # If status changed (either became too close or moved away to clear)
            if current_status[cls] != close_status[cls]:
                # If now too close
                if current_status[cls]:
                    message = f"{cls} approaching from the {class_position_status[cls]}."
                    print(message)
                    synthesize_speech_async(message)
                # If now clear
                else:
                    message = f"{cls} clear, you can proceed."
                    print(message)
                    synthesize_speech_async(message)
                # Update stored status
                close_status[cls] = current_status[cls]
        # If class was previously too close but not detected in this frame (thus clear)
        elif close_status[cls]:
            message = f"{cls} clear, you can proceed."
            print(message)
            synthesize_speech_async(message)
            close_status[cls] = False  # Reset status


    cv2.imshow("Frame", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()