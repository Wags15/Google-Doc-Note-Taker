import os
import openai

# Load OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("Error: OPENAI_API_KEY environment variable is not set.")


client = openai.OpenAI(api_key=OPENAI_API_KEY)


def summarize_text(text):
    """Uses OpenAI GPT to summarize the transcription."""
    if not text.strip():
        return "No transcription available to summarize."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "The following is a transcript from a university lecture. Summarize key points, dates, names, etc. that will help me study when I look back at my notes. Focus on content that could be on a test. Use point form when possible, but respond with only plain text. Do not bold, or format it other than the jot notes"},
                {"role": "user", "content": text}
            ]
        )
        summary = response.choices[0].message.content.strip()
        print("\n=== Summary ===\n", summary)
        return summary
    except Exception as e:
        print("Error during summarization:", e)
        return "Summary could not be generated."
