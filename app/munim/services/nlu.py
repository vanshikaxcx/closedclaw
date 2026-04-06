"""
Voice NLU Engine - Natural Language Understanding for Hindi/English
Handles speech-to-text and intent classification
"""
import re
from typing import Dict, Any, Optional, Tuple
import httpx
from groq import Groq

from app.munim.config import get_munim_config

config = get_munim_config()


class VoiceNLUEngine:
    """Voice-first NLU pipeline for Hindi/English"""
    
    def __init__(self):
        self.groq_client = None
        if config.GROQ_API_KEY:
            self.groq_client = Groq(api_key=config.GROQ_API_KEY)
    
    async def transcribe_audio(self, audio_data: bytes, filename: str = "audio.wav") -> str:
        """
        Transcribe audio to text using Groq Whisper (primary) or OpenAI Whisper (fallback)
        Supports: wav, mp3, ogg, m4a, webm
        """
        print(f"[NLU] Transcribing audio file: {filename} ({len(audio_data)} bytes)")
        
        # Try Groq Whisper first (it's faster and free)
        if self.groq_client:
            try:
                print("[NLU] Attempting Groq Whisper transcription...")
                transcription = await self._transcribe_groq(audio_data, filename)
                if transcription:
                    print(f"[NLU] Groq Whisper success: {transcription}")
                    return transcription
            except Exception as e:
                print(f"[NLU] Groq Whisper failed: {e}, falling back to OpenAI")
        
        # Fallback to OpenAI Whisper
        if config.OPENAI_API_KEY:
            try:
                print("[NLU] Attempting OpenAI Whisper transcription...")
                transcription = await self._transcribe_openai(audio_data, filename)
                if transcription:
                    print(f"[NLU] OpenAI Whisper success: {transcription}")
                    return transcription
            except Exception as e:
                print(f"[NLU] OpenAI Whisper failed: {e}")
                raise Exception(f"All STT services failed: {e}")
        
        raise Exception("No STT service configured (need GROQ_API_KEY or OPENAI_API_KEY)")
    
    async def _transcribe_openai(self, audio_data: bytes, filename: str) -> str:
        """Transcribe using OpenAI Whisper API"""
        async with httpx.AsyncClient() as client:
            files = {"file": (filename, audio_data, self._get_mime_type(filename))}
            headers = {"Authorization": f"Bearer {config.OPENAI_API_KEY}"}
            data = {
                "model": "whisper-1",
                "language": "hi",  # Hindi
                "response_format": "json",
                "temperature": 0.0
            }
            
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            return result.get("text", "").strip()
    
    async def _transcribe_groq(self, audio_data: bytes, filename: str) -> str:
        """Transcribe using Groq Whisper API"""
        # Groq Whisper supports: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, webm
        async with httpx.AsyncClient() as client:
            files = {"file": (filename, audio_data, self._get_mime_type(filename))}
            headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}
            data = {
                "model": config.GROQ_WHISPER_MODEL,
                "language": "hi",  # Hindi
                "response_format": "json",
                "temperature": 0.0
            }
            
            response = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            return result.get("text", "").strip()
    
    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type from filename"""
        ext = filename.lower().split('.')[-1]
        mime_types = {
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "ogg": "audio/ogg",
            "m4a": "audio/m4a",
            "webm": "audio/webm",
            "flac": "audio/flac",
            "mp4": "audio/mp4",
            "mpeg": "audio/mpeg",
            "mpga": "audio/mpeg"
        }
        return mime_types.get(ext, "audio/wav")
    
    def parse_hindi_numerals(self, text: str) -> str:
        """
        Parse Hindi numerals to numbers
        Examples: "dedh lakh" → "150000", "paanch hazaar" → "5000"
        """
        text = text.lower()
        
        # Hindi numeral mappings
        replacements = {
            "ek": "1",
            "do": "2",
            "teen": "3",
            "char": "4",
            "paanch": "5",
            "chhe": "6",
            "saat": "7",
            "aath": "8",
            "nau": "9",
            "das": "10",
            "bees": "20",
            "tees": "30",
            "chalis": "40",
            "pachas": "50",
            "saath": "60",
            "sattar": "70",
            "assi": "80",
            "nabbe": "90",
            "sau": "100",
            "hazaar": "1000",
            "lakh": "100000",
            "crore": "10000000",
            "dedh": "1.5",
            "dhai": "2.5",
            "sava": "1.25",
            "paune": "0.75"
        }
        
        for hindi, num in replacements.items():
            text = text.replace(hindi, num)
        
        return text
    
    async def classify_intent(self, text: str) -> Dict[str, Any]:
        """
        Classify intent and extract entities using Groq LLM
        Returns: {intent, confidence, entities: {amount, party_name, payment_mode}}
        """
        if not self.groq_client:
            # Mock mode
            return self._mock_classify_intent(text)
        
        # Parse Hindi numerals first
        processed_text = self.parse_hindi_numerals(text)
        
        prompt = f"""You are a financial assistant for Indian merchants. Analyze this voice command and extract:
1. Intent (one of: add_income, add_expense, add_udhari, query_balance, query_udhari, query_gst, query_forecast, query_payscore, query_schemes, create_autopay, query_customers, general_query)
2. Entities: amount (number), party_name (string), payment_mode (cash/upi/card)

Voice command: "{processed_text}"

Respond in JSON format:
{{
  "intent": "intent_name",
  "confidence": 0.95,
  "entities": {{
    "amount": 5000,
    "party_name": "Customer Name",
    "payment_mode": "upi"
  }}
}}"""
        
        try:
            response = self.groq_client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content
            # Extract JSON from response
            import json
            # Find JSON in response
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                return self._mock_classify_intent(text)
        
        except Exception as e:
            print(f"Intent classification failed: {e}")
            return self._mock_classify_intent(text)
    
    def _mock_classify_intent(self, text: str) -> Dict[str, Any]:
        """Mock intent classification for testing"""
        text_lower = text.lower()
        
        # Simple keyword-based classification
        if any(word in text_lower for word in ["income", "received", "mila", "aaya"]):
            intent = "add_income"
        elif any(word in text_lower for word in ["expense", "paid", "diya", "kharcha"]):
            intent = "add_expense"
        elif any(word in text_lower for word in ["udhari", "credit", "baki", "due"]):
            intent = "add_udhari"
        elif any(word in text_lower for word in ["balance", "kitna", "total"]):
            intent = "query_balance"
        else:
            intent = "general_query"
        
        # Extract amount using regex
        amount = None
        amount_match = re.search(r'(\d+(?:\.\d+)?)', text)
        if amount_match:
            amount = float(amount_match.group(1))
        
        # Extract payment mode
        payment_mode = None
        if "upi" in text_lower or "online" in text_lower:
            payment_mode = "upi"
        elif "cash" in text_lower or "nakad" in text_lower:
            payment_mode = "cash"
        
        return {
            "intent": intent,
            "confidence": 0.85,
            "entities": {
                "amount": amount,
                "party_name": None,
                "payment_mode": payment_mode
            }
        }
    
    async def process_voice_command(self, audio_data: bytes, filename: str = "audio.wav") -> Dict[str, Any]:
        """
        End-to-end voice command processing
        Returns: {transcription, intent, confidence, entities}
        """
        # Step 1: Transcribe audio
        transcription = await self.transcribe_audio(audio_data, filename)
        
        # Step 2: Classify intent and extract entities
        classification = await self.classify_intent(transcription)
        
        return {
            "transcription": transcription,
            "intent": classification["intent"],
            "confidence": classification["confidence"],
            "entities": classification["entities"]
        }


# Singleton instance
_nlu_engine = None

def get_nlu_engine() -> VoiceNLUEngine:
    """Get NLU engine singleton"""
    global _nlu_engine
    if _nlu_engine is None:
        _nlu_engine = VoiceNLUEngine()
    return _nlu_engine
