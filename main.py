from ultralytics import YOLO
import cv2
import math
import os

# Initialize webcam capture
cap = cv2.VideoCapture(0)  # 0 is usually the default camera

# Create a window named 'Frame'
cv2.namedWindow("Frame", cv2.WINDOW_NORMAL)

# Set the window to fullscreen
cv2.setWindowProperty("Frame", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# model
model = YOLO("yolo-Weights/yolov8n.pt")

# object classes
classNames = ["person", "bicycle", "car",  "bus"]

interested_classes = {"person", "bicycle", "car", "bus"}
min_confidence = 0.5

while True:
    success, img = cap.read()
    if not success:
        break  # Exit the loop if there's an error

    # Resize the frame to 1920x1080 for fullscreen display
    img = cv2.resize(img, (1920, 1080))

    results = model(img, stream=True)

    # coordinates
    for r in results:
        boxes = r.boxes

        for box in boxes:
            # bounding box
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)  # convert to int values

            # confidence
            confidence = math.ceil((box.conf[0]*100))/100
            print("Confidence --->", confidence)

            if confidence >= min_confidence:
                if len(box.cls) > 0:
                    cls = int(box.cls[0])
                    if cls < len(classNames) and classNames[cls] in interested_classes:
                        print("Class name -->", classNames[cls])

                        # Only draw box and label if the detected class is within the interested classes
                        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 255), 3)
                        org = [x1, y1]
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        fontScale = 1
                        color = (255, 0, 0)
                        thickness = 2

                        cv2.putText(img, f"{classNames[cls]}: {confidence:.2f}", org, font, fontScale, color, thickness)

    # Display the frame with detections
    cv2.imshow("Frame", img)

    # Break the loop when 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release everything when job is finished
cap.release()
cv2.destroyAllWindows()
