import gradio as gr
from assignment2_chat.main import travel_assistant_chat
from dotenv import load_dotenv
import os

from utils.logger import get_logger

_logs = get_logger(__name__)

load_dotenv('.secrets')

if not os.environ.get("OPENAI_API_KEY"):
    _logs.error("Missing OPENAI_API_KEY environment variable")
    raise ValueError("Missing OPENAI_API_KEY environment variable")

if not os.environ.get("WEATHERSTACK_API_KEY"):
    _logs.warning("Missing WEATHERSTACK_API_KEY environment variable - weather service will not work")

chat = gr.ChatInterface(
    fn=travel_assistant_chat,
    type="messages",
    title="Assignment 2: Jason Pereira's Travel Assistant",
    description="A friendly travel assistant ready to help with current weather, destination city information, and currency conversion!",
    theme="soft",
    examples=[
        "What's the weather like in Paris?",
        "Tell me about London",
        "Convert 200 CAD to EUR",
        "I'm planning a trip to Europe - can you help?"
    ],
    cache_examples=False,
    css="""
        * {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        }
    """
)

if __name__ == "__main__":
    _logs.info('Starting Travel Assistant Chat App...')
    chat.launch()

