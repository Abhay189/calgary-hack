import moviepy.editor as mp
import speech_recognition as sr
import openai

# Assuming you've set your OpenAI API key in your environment variables:
# export OPENAI_API_KEY='your_api_key_here'
openai.api_key = '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'

def extract_audio(video_path, audio_path):
    video = mp.VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path)
    return audio_path

def transcribe_audio(audio_file_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file_path) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
            return text
        except sr.UnknownValueError:
            return "Audio was not understood"
        except sr.RequestError as e:
            return f"Could not request results from Google Speech Recognition service; {e}"

def process_video_and_get_feedback(video_file_path):
    # Extract audio from the video
    audio_file_path = extract_audio(video_path=video_file_path, audio_path="output_audio.wav")

    transcribed_text = transcribe_audio(audio_file_path)
    print(transcribed_text)
    
    # Prepare the conversation for AI feedback
    question = "Tell Us About The Biggest Challenge Youve Ever Faced"
    answer = transcribed_text
    conversations = [
        {
            "role": "system",
            "content": (
                "You are an expert interview preparation assistant. Your goal is to provide "
                "constructive feedback and suggestions for improvement when given interview "
                "questions and a user's transcribed audio response. Emphasize clarity, relevance, "
                "and professionalism in your feedback. Please format the feedback for HTML display. "
                "Use <p> for paragraphs, <br> for new lines, <ul> or <ol> for lists, and <strong> for "
                "emphasis. Ensure the feedback is well-structured and easy to read in an HTML document."
            )
        },
        {
            "role": "user",
            "content": f"The question asked in the interview is this: {question} The transcribed response is: {answer} Provide feedback to improve my response to ace the interview."
        }
    ]

    # Generate a response using OpenAI GPT
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=conversations
    )

    # Get the AI's response
    ai_response = response.choices[0].message['content']
    print(ai_response)
    return ai_response

if __name__ == "__main__":
    video_file_path = "path_to_your_video.mp4"  # Update this path
    feedback = process_video_and_get_feedback(video_file_path)
    print(feedback)
