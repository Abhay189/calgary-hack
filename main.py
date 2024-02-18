from ultralytics import YOLO
import cv2
import math
import os
# import sys
# other imports remain the same

# Use the first command-line argument as the video path
# Load a video file instead of webcam
video_path = 'videos/scene6_pov.mp4'  # Replace with your video file path
# video_path = ''
# # Check if the video path was provided as a command-line argument
# if len(sys.argv) > 1:
#     video_path = sys.argv[1]
# else:
#     print("Please provide a video path as a command-line argument.")
    # sys.exit(1)  # Exit the script if no argument is provided

cap = cv2.VideoCapture(video_path)
video_filename_with_extension = os.path.basename(video_path)

# Get video properties to use with the video writer
frame_width = int(cap.get(3))
frame_height = int(cap.get(4))
fps = int(cap.get(cv2.CAP_PROP_FPS))

# Define the codec for MP4 format and create VideoWriter object
# Note: On some systems, you might need to use 'avc1' instead of 'mp4v' as the codec.
# final_video_path = f"./processed_video/{video_path}"
out = cv2.VideoWriter(f'{video_filename_with_extension}', cv2.VideoWriter_fourcc(*'mp4v'), fps, (frame_width, frame_height))


# model
model = YOLO("yolo-Weights/yolov8n.pt")

# object classes
classNames = ["person", "bicycle", "car",  "bus"]

interested_classes = {"person", "bicycle", "car", "bus"}
min_confidence = 0.5

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

    # Write the frame with detections to the output video
    out.write(img)

# Release everything when job is finished
cap.release()
out.release()
cv2.destroyAllWindows()
