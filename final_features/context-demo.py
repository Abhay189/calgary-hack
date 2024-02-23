from IPython.display import display, Image, Audio

import cv2  # We're using OpenCV to read video, to install !pip install opencv-python
import base64
import time
from openai import OpenAI
import os
import requests
import boto3
from pydub import AudioSegment
from pydub.playback import play
from io import BytesIO
from pygame import mixer
from contextlib import closing
import speech_recognition as sr


def synthesize_speech(text):
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


def listen_for_question():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for 'hey vision'...")
        audio = recognizer.listen(source)
        try:
            # Recognize speech using Google Speech Recognition
            transcription = recognizer.recognize_google(audio)
            print(f"Transcription: {transcription}")
            if "hey vision" in transcription.lower():
                print("Wake word detected. Listening for question...")
                audio_question = recognizer.listen(source)
                question = recognizer.recognize_google(audio_question)
                print(f"Question: {question}")
                return question
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
    return None


# Define the directory and file name
directory = "data"
filename = "bison.mp4"
filepath = os.path.join(directory, filename)

# Ensure the directory exists
if not os.path.exists(directory):
    os.makedirs(directory)

# Define the codec and create VideoWriter object to save the video
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
fps = 20.0
frame_size = (640, 480)
out = cv2.VideoWriter(filepath, fourcc, fps, frame_size)

# Start video capture from the webcam
cap = cv2.VideoCapture(0)

# Set the duration for the video capture
capture_duration = 5
start_time = time.time()

while int(time.time() - start_time) < capture_duration:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break
    out.write(frame)  # Save the frame to the file

    # Optionally display the frame during capture
    cv2.imshow('Recording...', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
out.release()
cv2.destroyAllWindows()

print(f"Video saved as {filepath}")
time.sleep(2)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "OPENAI_API_KEY"))

video = cv2.VideoCapture("data/bison.mp4")

base64Frames = []

while video.isOpened():
    success, frame = video.read()
    if not success:
        break
    _, buffer = cv2.imencode(".jpg", frame)
    base64Frames.append(base64.b64encode(buffer).decode("utf-8"))

video.release()
print(f"{len(base64Frames)} frames read.")

#display_handle = display(None, display_id=True)
for img in base64Frames:
    #display_handle.update(Image(data=base64.b64decode(img.encode("utf-8"))))
    time.sleep(0.025)

    PROMPT_MESSAGES = [
    {
        "role": "user",
        "content": [
            "We're analyzing key frames from a video, intended to be described to a visually impaired audience. The video is captured via a wearable webcam, and our goal is to narrate each frame's content to convey what's happening visually but dont explicitly say the words 'frame' or 'image' or 'scene', say it like a combined summary but capture as much information from the frame as possible (like if its a person observe their ethicity, age etc. If its money note the currency and amount). This will help visually impaired viewers understand the scenes as if they were seeing them. The frames, selected at regular intervals, are resized for clarity and focus on capturing diverse moments throughout the video. If there was a text shown in any of the frame mention the extracted text in quotes",
            *map(lambda x: {"image": x, "resize": 768}, base64Frames[0::50]),
        ],
    },
]
params = {
    "model": "gpt-4-vision-preview",
    "messages": PROMPT_MESSAGES,
    "max_tokens": 200,
}

result = client.chat.completions.create(**params)
videoContext = result.choices[0].message.content

print(videoContext)

while True:
    question = listen_for_question()
    if question:
        # Replace userQuestion with the transcribed question
        userQuestion = question
        
        conversations = [
            {"role": "system", "content": "You are a virtual assistant designed to assist a visually impaired person. Your responses should be based on interpreting a detailed description of a video feed as if the visually impaired person is 'seeing' through the video. The video context you'll use to answer questions is: " + videoContext},
            {"role": "user", "content": userQuestion + "Give concise 1-2 senetence response"}
        ]

        response = client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=conversations
                )
        response_text = response.choices[0].message.content

        print(response_text)

        # Here, insert the code to process the question, call your model, and synthesize speech
        # For demonstration, we'll just synthesize the question itself
        synthesize_speech(response_text)
