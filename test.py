from openai import OpenAI
import os
import speech_recognition as sr
import pyttsx3
import cv2
import threading

# Webcam capture function
def webcam_capture():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return  # Exit the function if the webcam cannot be opened

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Can't receive frame (stream end?). Exiting ...")
            break

        cv2.imshow('Webcam Live', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# Function to initialize and run the speech recognition and response logic
def speech_to_text_and_response():
    # Initialize speech recognition
    recognizer = sr.Recognizer()

    # Initialize text-to-speech engine
    tts_engine = pyttsx3.init()

    # Setup OpenAI client with API key
    os.environ["OPENAI_API_KEY"] = 'dummy'
    client = OpenAI()

    with sr.Microphone() as source:
        print("Please speak your response...")
        audio = recognizer.listen(source)

    try:
        transcribed_text = recognizer.recognize_google(audio)
        print("You said: " + transcribed_text)

        # Prepare the conversation for ChatGPT
        conversations = [
            {"role": "system", "content": "Your job is to answer questions related to an ice cream menu."},
            {"role": "user", "content": f"{transcribed_text} Provide concise response"}
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=conversations
        )

        response_text = response.choices[0].message.content
        print(response_text)

        tts_engine.say(response_text)
        tts_engine.runAndWait()

    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")

# Start the webcam capture in a separate thread
webcam_thread = threading.Thread(target=webcam_capture)
webcam_thread.start()

# Run the speech to text and response logic in the main thread
speech_to_text_and_response()

# Join the webcam thread to ensure it closes properly when the main thread is done
webcam_thread.join()
