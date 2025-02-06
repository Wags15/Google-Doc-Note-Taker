# Google-Doc-Note-Taker

Uses pyaudio to stream audio from the device microphone.

Google Cloud Text-To-Speech is used to transcribe the audio to text as it comes in in chunks.

Google Docs API is used to append the transribed text to the Google Doc of the user's choice.

Once the transcript is complete, it gets summarized through openAI's gpt-4o-mini model. This summarization gets added to a separate Google Doc that contains all previous summaries

# How to Use 

Run the script and pass in a title that the transcription will be placed under. Upon running, there is a dropdown of 4 courses to select from. Select the course for which you want to take notes for and the script takes care of the rest. 
