from ultralytics import YOLO
import cv2
import math

# Load a video file instead of webcam
video_path = './Videos/PXL_20240218_012740321.mp4'  # Replace with your video file path
cap = cv2.VideoCapture(video_path)

# Set resolution - remove if you want to use the video's original resolution
cap.set(3, 640)  # Width
cap.set(4, 480)  # Height

# model
model = YOLO("yolo-Weights/yolov8n.pt")

# object classes
classNames = ["person", "bicycle", "car" , "truck" ,"motorcycle" , "traffic light" ,"stop sign"]
interested_classes = ["person", "bicycle", "car" , "truck" ,"motorcycle" , "traffic light" ,"stop sign"]

while True:
    success, img = cap.read()
    if not success:
        print("Finished processing video.")
        break  # Exit the loop if video ends or there's an error

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
                else:
                    print("Detected class not in interested classes:", classNames[cls] if cls < len(classNames) else "Unknown")


    cv2.imshow('Video', img)
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
