import os
import pyaudio
import queue
from google.cloud import speech
from google.oauth2 import service_account
from googleapiclient.discovery import build
import sys
import os

CLST_201 = os.getenv('CLST_201_ID')

if not CLST_201:
    print("ERROR: Missing env variables")
    sys.exit(1)

GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID')
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
STORAGE_BUCKET_NAME = os.getenv('STORAGE_BUCKET_NAME')

# Set up credentials
GOOGLE_CLOUD_CREDENTIALS = "service-key.json"
credentials = service_account.Credentials.from_service_account_file(
    GOOGLE_CLOUD_CREDENTIALS)
speech_client = speech.SpeechClient(credentials=credentials)
docs_service = build('docs', 'v1', credentials=credentials)

# Google Docs ID
DOCUMENT_ID = CLST_201

# Audio streaming settings
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms chunks

# Queue for real-time streaming
audio_queue = queue.Queue()


def record_callback(in_data, frame_count, time_info, status):
    """Callback function to stream audio data."""
    audio_queue.put(in_data)
    return (None, pyaudio.paContinue)


def transcribe_streaming():
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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py 'Title of the Transcription'")
        sys.exit(1)

    title = sys.argv[1]
    append_title_to_google_doc(DOCUMENT_ID, title)
    print("Starting real-time transcription. Speak into the microphone...")
    transcribe_streaming()
