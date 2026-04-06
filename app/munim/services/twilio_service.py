"""
Twilio Service for WhatsApp, SMS, and Voice
"""
import os
from twilio.rest import Client
from app.munim.config import get_munim_config

config = get_munim_config()


class TwilioService:
    """Handles Twilio communications"""
    
    def __init__(self):
        self.client = None
        if config.is_configured("twilio"):
            self.client = Client(
                config.TWILIO_ACCOUNT_SID,
                config.TWILIO_AUTH_TOKEN
            )
    
    def _get_phone_number(self, to_phone: str) -> str:
        """Apply phone override if configured"""
        override_phone = os.getenv("WHATSAPP_OVERRIDE_PHONE", "").strip()
        if override_phone:
            print(f"[Twilio] Overriding phone {to_phone} with {override_phone}")
            return override_phone
        return to_phone
    
    def send_whatsapp(self, to_phone: str, message: str) -> dict:
        """
        Send WhatsApp message via Twilio
        
        Args:
            to_phone: Recipient phone number (e.g., "+919999999999")
            message: Message text
            
        Returns:
            dict with 'success', 'sid', 'error' keys
        """
        if not self.client:
            return {
                "success": False,
                "error": "Twilio not configured",
                "sid": None
            }
        
        try:
            # Apply phone override
            to_phone = self._get_phone_number(to_phone)
            
            # Ensure phone number has whatsapp: prefix
            if not to_phone.startswith("whatsapp:"):
                to_phone = f"whatsapp:{to_phone}"
            
            message_obj = self.client.messages.create(
                from_=config.TWILIO_WHATSAPP_NUMBER,
                to=to_phone,
                body=message
            )
            
            return {
                "success": True,
                "sid": message_obj.sid,
                "status": message_obj.status,
                "error": None
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sid": None
            }
    
    def send_sms(self, to_phone: str, message: str) -> dict:
        """
        Send SMS via Twilio
        
        Args:
            to_phone: Recipient phone number (e.g., "+919999999999")
            message: Message text
            
        Returns:
            dict with 'success', 'sid', 'error' keys
        """
        if not self.client:
            return {
                "success": False,
                "error": "Twilio not configured",
                "sid": None
            }
        
        try:
            # Apply phone override
            to_phone = self._get_phone_number(to_phone)
            
            message_obj = self.client.messages.create(
                from_=config.TWILIO_PHONE_NUMBER,
                to=to_phone,
                body=message
            )
            
            return {
                "success": True,
                "sid": message_obj.sid,
                "status": message_obj.status,
                "error": None
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sid": None
            }
    
    def make_voice_call(self, to_phone: str, message: str) -> dict:
        """
        Make voice call via Twilio (using TwiML)
        
        Args:
            to_phone: Recipient phone number (e.g., "+919999999999")
            message: Message to speak
            
        Returns:
            dict with 'success', 'sid', 'error' keys
        """
        if not self.client:
            return {
                "success": False,
                "error": "Twilio not configured",
                "sid": None
            }
        
        try:
            # Apply phone override
            to_phone = self._get_phone_number(to_phone)
            
            # Create TwiML for voice message
            twiml = f'<Response><Say language="hi-IN">{message}</Say></Response>'
            
            call = self.client.calls.create(
                from_=config.TWILIO_PHONE_NUMBER,
                to=to_phone,
                twiml=twiml
            )
            
            return {
                "success": True,
                "sid": call.sid,
                "status": call.status,
                "error": None
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sid": None
            }


# Singleton instance
_twilio_service = None

def get_twilio_service() -> TwilioService:
    """Get Twilio service singleton"""
    global _twilio_service
    if _twilio_service is None:
        _twilio_service = TwilioService()
    return _twilio_service
