from groq import Groq

from app.core.config import settings


def get_groq_client() -> Groq:
    """Create a Groq API client using the configured API key."""
    return Groq(api_key=settings.groq_api_key)