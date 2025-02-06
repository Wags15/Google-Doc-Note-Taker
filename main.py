import os
import pyaudio
import inquirer
import queue
from google.cloud import speech
from google.oauth2 import service_account
from googleapiclient.discovery import build
import sys
import os

from summarizer import summarize_text

DOC_OPTIONS = {
    "CLST 201": os.getenv("CLST_201_ID"),
    "CLST 150": os.getenv("CLST_150_ID"),
    "CISC 455": os.getenv("CISC_455_ID"),
    "CISC 474": os.getenv("CISC_474_ID")
}
SUMMARY_DOC_OPTIONS = {
    "CLST 201": os.getenv("SUMMARY_CLST_201_ID"),
    "CLST 150": os.getenv("SUMMARY_CLST_150_ID"),
    "CISC 455": os.getenv("SUMMARY_CISC_455_ID"),
    "CISC 474": os.getenv("SUMMARY_CISC_474_ID")
}

# Ensure all DOC_ID environment variables are set
if not all(DOC_OPTIONS.values()) and not all(SUMMARY_DOC_OPTIONS.values()):
    print("Error: One or more DOC_ID environment variables are missing.")
    sys.exit(1)

# Set up credentials
GOOGLE_CLOUD_CREDENTIALS = "service-key.json"
credentials = service_account.Credentials.from_service_account_file(
    GOOGLE_CLOUD_CREDENTIALS)
speech_client = speech.SpeechClient(credentials=credentials)
docs_service = build('docs', 'v1', credentials=credentials)

# Ask user to choose a document
questions = [
    inquirer.List("doc_choice",
                  message="Select a course to save the transcription",
                  choices=list(DOC_OPTIONS.keys()))
]
answers = inquirer.prompt(questions)
DOCUMENT_ID = DOC_OPTIONS[answers["doc_choice"]]
SUMMARY_DOCUMENT_ID = SUMMARY_DOC_OPTIONS[answers["doc_choice"]]

# Audio streaming settings
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms chunks

# Queue for real-time streaming
audio_queue = queue.Queue()

full_transcription = ""  # Stores the complete transcription


def record_callback(in_data, frame_count, time_info, status):
    """Callback function to stream audio data."""
    audio_queue.put(in_data)
    return (None, pyaudio.paContinue)


def transcribe_streaming():
    global full_transcription  # Store transcription globally

    """Streams audio from microphone and transcribes in real-time."""
    audio_interface = pyaudio.PyAudio()
    stream = audio_interface.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK,
        stream_callback=record_callback
    )

    def audio_generator():
        """Yields audio chunks from the queue."""
        while True:
            chunk = audio_queue.get()
            if chunk is None:
                break
            yield speech.StreamingRecognizeRequest(audio_content=chunk)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="en-US",
    )

    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True  # Get partial results
    )

    responses = speech_client.streaming_recognize(
        streaming_config, audio_generator())

    for response in responses:
        for result in response.results:
            if result.is_final:
                transcript = result.alternatives[0].transcript
                full_transcription += transcript + " "
                print("Transcribed:", transcript)
                write_to_google_doc(DOCUMENT_ID, transcript)

    stream.stop_stream()
    stream.close()
    audio_interface.terminate()


def write_to_google_doc(document_id, text):
    """Appends transcribed text to Google Docs in real-time."""
    doc = docs_service.documents().get(documentId=document_id).execute()
    end_index = doc.get('body').get('content')[-1].get('endIndex') - 1

    requests = [
        {
            "insertText": {
                "location": {
                    "index": end_index
                },
                "text": text + "\n\n"
            }
        }
    ]

    docs_service.documents().batchUpdate(documentId=document_id,
                                         body={"requests": requests}).execute()
    print("Appended to Google Docs.")


def append_title_to_google_doc(document_id, title):
    """Adds the title in bold at the end of the Google Doc."""
    doc = docs_service.documents().get(documentId=document_id).execute()
    end_index = doc.get('body').get('content')[-1].get('endIndex') - 1

    requests = [
        {
            "insertText": {
                "location": {
                    "index": end_index
                },
                "text": title + "\n\n"
            }
        },
        {
            "updateTextStyle": {
                "range": {
                    "startIndex": end_index,
                    "endIndex": end_index + len(title)
                },
                "textStyle": {
                    "bold": True
                },
                "fields": "bold"
            }
        }
    ]

    docs_service.documents().batchUpdate(documentId=document_id,
                                         body={"requests": requests}).execute()
    print(f"Title '{title}' added to Google Docs.")


def summarize_and_save():
    """Summarizes the full transcription and saves it to Google Docs."""
    global full_transcription

    summary = summarize_text(full_transcription)
    append_summary_to_google_doc(SUMMARY_DOCUMENT_ID, summary)


def append_summary_to_google_doc(document_id, summary):
    """Appends the summary to the Google Doc."""
    doc = docs_service.documents().get(documentId=document_id).execute()
    end_index = doc.get('body').get('content')[-1].get('endIndex') - 1

    requests = [
        {
            "insertText": {
                "location": {
                    "index": end_index
                },
                "text": summary
            }
        },
        {
            "updateTextStyle": {
                "range": {
                    "startIndex": end_index + 1,
                    "endIndex": end_index + 12
                },
                "textStyle": {
                    "bold": True
                },
                "fields": "bold"
            }
        }
    ]

    docs_service.documents().batchUpdate(documentId=document_id,
                                         body={"requests": requests}).execute()
    print("Summary appended to Google Docs.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py 'Title of the Transcription'")
        sys.exit(1)

    title = sys.argv[1]
    append_title_to_google_doc(DOCUMENT_ID, title)
    append_title_to_google_doc(SUMMARY_DOCUMENT_ID, title)

    print("Starting real-time transcription. Speak into the microphone...")

    try:
        transcribe_streaming()
    except KeyboardInterrupt:
        print("\nManual stop detected. Summarizing transcription...")
        summarize_and_save()
        sys.exit(0)
