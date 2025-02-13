from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPEN_API_KEY"))

def generate_summary(event_title: str) -> str:
    """
    Generates a factual historical summary of the given event using OpenAI's GPT-4.

    Args:
        event_title (str): The historical event to summarize.

    Returns:
        str: The AI-generated summary.

    Raises:
        Exception: If the OpenAI API call fails.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a historian. Provide a factual summary with key events. "
                               "Format: Plain text with citations as [1], [2] where needed."
                },
                {
                    "role": "user",
                    "content": f"Summarize major events of {event_title} with context and significance."
                }
            ],
            temperature=0.5  # Lowered for more factual accuracy
        )
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        return f"❌ Error generating summary: {str(e)}"
