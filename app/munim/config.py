"""
Arthsetu Merchant Help Configuration
"""
import os
from typing import List
from functools import lru_cache
from dotenv import load_dotenv

# Load .env.munim file
load_dotenv('.env.munim')


class MunimConfig:
    """Arthsetu Merchant Help configuration settings"""
    
    # Groq API
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_WHISPER_MODEL: str = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3")
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Twilio
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_NUMBER: str = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    
    # Tavily
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    
    # Sarvam AI
    SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")
    
    # Socket.IO
    SOCKETIO_CORS_ORIGINS: List[str] = os.getenv(
        "SOCKETIO_CORS_ORIGINS", 
        "http://localhost:3000,http://localhost:3001"
    ).split(",")
    
    # Feature Flags
    MOCK_MODE: bool = os.getenv("MUNIM_MOCK_MODE", "true").lower() == "true"
    SEED_DEMO_DATA: bool = os.getenv("MUNIM_SEED_DEMO_DATA", "true").lower() == "true"
    
    @classmethod
    def is_configured(cls, service: str) -> bool:
        """Check if a service is configured"""
        if service == "groq":
            return bool(cls.GROQ_API_KEY)
        elif service == "openai":
            return bool(cls.OPENAI_API_KEY)
        elif service == "twilio":
            return bool(cls.TWILIO_ACCOUNT_SID and cls.TWILIO_AUTH_TOKEN)
        elif service == "tavily":
            return bool(cls.TAVILY_API_KEY)
        elif service == "sarvam":
            return bool(cls.SARVAM_API_KEY)
        return False


@lru_cache()
def get_munim_config() -> MunimConfig:
    """Get Arthsetu Merchant Help configuration singleton"""
    return MunimConfig()
