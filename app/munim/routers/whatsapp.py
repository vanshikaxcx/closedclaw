"""
WhatsApp Router - Handle incoming/outgoing WhatsApp messages
"""
from fastapi import APIRouter, HTTPException, Request, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import json

from app.munim.services.twilio_service import get_twilio_service
from app.munim.services.nlu import get_nlu_engine
from app.munim.services.briefing import get_briefing_service
from app.munim.data.mock_store import add_to_collection, filter_collection, get_collection

router = APIRouter(prefix="/api/munim/whatsapp")

# Conversation state storage (in-memory for demo)
CONVERSATION_STATE: Dict[str, Dict[str, Any]] = {}


class WhatsAppSendRequest(BaseModel):
    merchant_id: str
    phone: str
    message: str


class WhatsAppBriefingRequest(BaseModel):
    merchant_id: str
    phone: str


@router.post("/send")
async def send_whatsapp_message(request: WhatsAppSendRequest):
    """
    Send WhatsApp message to a phone number
    
    Args:
        merchant_id: Merchant ID
        phone: Recipient phone number
        message: Message text
        
    Returns:
        Success status and message SID
    """
    twilio_service = get_twilio_service()
    
    result = twilio_service.send_whatsapp(request.phone, request.message)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    # Store message in history
    add_to_collection("whatsapp_messages", {
        "id": result["sid"],
        "merchant_id": request.merchant_id,
        "phone": request.phone,
        "message": request.message,
        "direction": "outbound",
        "status": result.get("status", "sent"),
        "created_at": datetime.utcnow().isoformat()
    })
    
    return {
        "success": True,
        "sid": result["sid"],
        "status": result.get("status")
    }


@router.post("/briefing")
async def send_daily_briefing(request: WhatsAppBriefingRequest):
    """
    Send daily briefing to merchant
    
    Args:
        merchant_id: Merchant ID
        phone: Merchant's WhatsApp phone number
        
    Returns:
        Briefing sent status
    """
    briefing_service = get_briefing_service()
    
    result = await briefing_service.send_daily_briefing(
        request.merchant_id,
        request.phone
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@router.post("/briefing/all")
async def send_briefings_to_all():
    """
    Send daily briefings to all merchants (for scheduled job)
    
    Returns:
        Summary of briefings sent
    """
    briefing_service = get_briefing_service()
    
    result = await briefing_service.send_briefings_to_all_merchants()
    
    return result


@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: Optional[str] = Form(""),
    MessageSid: Optional[str] = Form(None),
    MediaUrl0: Optional[str] = Form(None),
    MediaContentType0: Optional[str] = Form(None),
    NumMedia: Optional[str] = Form("0")
):
    """
    Twilio WhatsApp webhook - receives incoming messages
    
    Handles:
    - Text commands
    - Voice notes (audio messages)
    - Invoice photos (images)
    
    Args:
        From: Sender's WhatsApp number (whatsapp:+919999999999)
        Body: Message text (optional, empty for media-only messages)
        MessageSid: Twilio message SID
        MediaUrl0: URL of first media attachment
        MediaContentType0: Content type of first media
        NumMedia: Number of media attachments
        
    Returns:
        TwiML response
    """
    # Extract phone number
    phone = From.replace("whatsapp:", "")
    
    # Log incoming message
    print(f"[WhatsApp Webhook] From: {phone}, Body: '{Body}', Media: {MediaUrl0}, Type: {MediaContentType0}")
    
    # Store incoming message
    message_data = {
        "id": MessageSid or f"msg_{datetime.utcnow().timestamp()}",
        "phone": phone,
        "message": Body or "",
        "direction": "inbound",
        "media_url": MediaUrl0,
        "media_type": MediaContentType0,
        "created_at": datetime.utcnow().isoformat()
    }
    add_to_collection("whatsapp_messages", message_data)
    
    # Get or create conversation state
    if phone not in CONVERSATION_STATE:
        CONVERSATION_STATE[phone] = {
            "merchant_id": "demo_merchant",  # In production, lookup merchant by phone
            "last_command": None,
            "context": {}
        }
    
    state = CONVERSATION_STATE[phone]
    merchant_id = state["merchant_id"]
    
    # Process message based on type
    response_text = ""
    
    try:
        # Handle media messages
        if MediaUrl0:
            if MediaContentType0 and MediaContentType0.startswith("audio"):
                # Voice note - transcribe and process
                print(f"[WhatsApp Webhook] Processing voice note from {phone}")
                response_text = await handle_voice_note(MediaUrl0, merchant_id, state)
            elif MediaContentType0 and MediaContentType0.startswith("image"):
                # Invoice photo - OCR and process
                print(f"[WhatsApp Webhook] Processing image from {phone}")
                response_text = await handle_invoice_photo(MediaUrl0, merchant_id, state)
            else:
                response_text = "माफ़ करें, मैं इस प्रकार की फ़ाइल को समझ नहीं सकता। कृपया टेक्स्ट, वॉइस नोट या इनवॉइस फोटो भेजें।"
        
        # Handle text commands (only if no media or body is not empty)
        elif Body and Body.strip():
            print(f"[WhatsApp Webhook] Processing text command from {phone}")
            response_text = await handle_text_command(Body, merchant_id, state)
        
        # Empty message (shouldn't happen, but handle gracefully)
        else:
            print(f"[WhatsApp Webhook] Empty message from {phone}")
            response_text = "नमस्ते! 🙏 कृपया कोई कमांड या वॉइस नोट भेजें।"
    
    except Exception as e:
        print(f"[WhatsApp Webhook] Error processing message: {e}")
        import traceback
        traceback.print_exc()
        response_text = "माफ़ करें, कुछ गलत हो गया। कृपया फिर से कोशिश करें।"
    
    # Send response back to user
    twilio_service = get_twilio_service()
    twilio_service.send_whatsapp(phone, response_text)
    
    # Return TwiML response (empty is fine, we already sent the message)
    return {"status": "processed"}


async def handle_text_command(text: str, merchant_id: str, state: Dict[str, Any]) -> str:
    """
    Handle text command from WhatsApp
    
    Supported commands:
    - "aaj ka hisaab" - Today's P&L summary
    - "udhari list" - Outstanding debts
    - "GST status" - GST filing status
    - "forecast" - Cash flow forecast
    
    Args:
        text: Command text
        merchant_id: Merchant ID
        state: Conversation state
        
    Returns:
        Response text
    """
    text_lower = text.lower().strip()
    
    # Command: Today's accounts
    if any(cmd in text_lower for cmd in ["aaj ka hisaab", "today", "आज का हिसाब"]):
        briefing_service = get_briefing_service()
        briefing_text = briefing_service.generate_briefing_text(merchant_id)
        return briefing_text
    
    # Command: Udhari list
    elif any(cmd in text_lower for cmd in ["udhari list", "udhari", "उधारी", "बाकी"]):
        udhari_list = filter_collection("udhari", {"merchant_id": merchant_id, "status": "pending"})
        
        if not udhari_list:
            return """🎉 बधाई हो! आपकी कोई उधारी बाकी नहीं है।

💡 टिप: नियमित लेन-देन से आपका PayScore बढ़ता है!"""
        
        # Sort by risk score (highest first)
        udhari_list_sorted = sorted(udhari_list, key=lambda u: u.get("risk_score", 0), reverse=True)
        
        # Calculate stats
        total = sum(u["amount"] for u in udhari_list)
        high_risk = [u for u in udhari_list if u.get("risk_score", 0) > 66]
        medium_risk = [u for u in udhari_list if 34 <= u.get("risk_score", 0) <= 66]
        
        response = "📋 बाकी उधारी:\n\n"
        
        # Show high risk first
        if high_risk:
            response += "⚠️ हाई रिस्क:\n"
            for i, udhari in enumerate(high_risk[:3], 1):
                response += f"{i}. {udhari['debtor_name']}: ₹{udhari['amount']:,.2f}\n"
                response += f"   📞 {udhari['debtor_phone']}\n"
                response += f"   🔴 रिस्क: {udhari['risk_score']}/100\n\n"
        
        # Show medium risk
        if medium_risk and len(high_risk) < 3:
            response += "⚡ मीडियम रिस्क:\n"
            remaining = 3 - len(high_risk)
            for i, udhari in enumerate(medium_risk[:remaining], 1):
                response += f"{i}. {udhari['debtor_name']}: ₹{udhari['amount']:,.2f}\n"
                response += f"   📞 {udhari['debtor_phone']}\n"
                response += f"   🟡 रिस्क: {udhari['risk_score']}/100\n\n"
        
        # Summary
        response += f"💰 कुल बाकी: ₹{total:,.2f}\n"
        response += f"👥 कुल लोग: {len(udhari_list)}\n\n"
        
        # Action items
        if high_risk:
            response += f"🎯 एक्शन: {len(high_risk)} हाई रिस्क उधारी पर फॉलो-अप करें"
        else:
            response += "✅ सभी उधारी कंट्रोल में हैं"
        
        return response
    
    # Command: GST status
    elif any(cmd in text_lower for cmd in ["gst status", "gst", "जीएसटी"]):
        from datetime import timedelta
        
        # Calculate dates
        today = datetime.utcnow().date()
        last_filing = today.replace(day=15) if today.day > 15 else (today.replace(day=1) - timedelta(days=1)).replace(day=15)
        next_filing = (today.replace(day=1) + timedelta(days=32)).replace(day=20)
        days_left = (next_filing - today).days
        
        # Get transactions for tax calculation
        transactions = filter_collection("transactions", {"merchant_id": merchant_id})
        current_month_txns = [
            t for t in transactions 
            if datetime.fromisoformat(t.get("created_at", "")).date().month == today.month
        ]
        
        # Calculate estimated tax (simplified)
        total_income = sum(t["amount"] for t in current_month_txns if t["type"] == "income")
        estimated_tax = total_income * 0.18  # 18% GST
        
        status_emoji = "✅" if days_left > 10 else "⚠️"
        urgency = "" if days_left > 10 else f"\n\n⏰ सिर्फ {days_left} दिन बाकी!"
        
        return f"""📊 GST स्थिति:

{status_emoji} पिछला फाइलिंग: {last_filing.strftime('%d %B %Y')}
📅 अगला फाइलिंग: {next_filing.strftime('%d %B %Y')}
💰 अनुमानित टैक्स: ₹{estimated_tax:,.2f}
📈 इस महीने की आय: ₹{total_income:,.2f}{urgency}

💡 टिप: समय पर फाइलिंग से पेनल्टी बचती है!"""
    
    # Command: Forecast
    elif any(cmd in text_lower for cmd in ["forecast", "भविष्यवाणी", "अनुमान"]):
        from datetime import timedelta
        
        # Get historical data
        transactions = filter_collection("transactions", {"merchant_id": merchant_id})
        
        # Calculate last 30 days average
        thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
        recent_txns = [
            t for t in transactions 
            if datetime.fromisoformat(t.get("created_at", "")).date() >= thirty_days_ago
        ]
        
        avg_daily_income = sum(t["amount"] for t in recent_txns if t["type"] == "income") / 30
        avg_daily_expense = sum(t["amount"] for t in recent_txns if t["type"] == "expense") / 30
        
        # Forecast for next 30 days
        forecast_income = avg_daily_income * 30
        forecast_expense = avg_daily_expense * 30
        forecast_profit = forecast_income - forecast_expense
        
        # Festival impact (example: Holi)
        festival_date = "25 मार्च"
        festival_boost = 30
        
        trend_emoji = "📈" if forecast_profit > 0 else "📉"
        
        return f"""📈 अगले 30 दिनों का अनुमान:

💰 अनुमानित आय: ₹{forecast_income:,.0f}
💸 अनुमानित खर्च: ₹{forecast_expense:,.0f}
{trend_emoji} अनुमानित लाभ: ₹{forecast_profit:,.0f}

🎉 होली ({festival_date}): +{festival_boost}% आय की उम्मीद

📊 पिछले 30 दिनों के आधार पर:
• औसत दैनिक आय: ₹{avg_daily_income:,.0f}
• औसत दैनिक खर्च: ₹{avg_daily_expense:,.0f}

💡 टिप: त्योहार से पहले स्टॉक तैयार रखें!"""
    
    # Use NLU for general commands
    else:
        nlu_engine = get_nlu_engine()
        classification = await nlu_engine.classify_intent(text)
        
        intent = classification["intent"]
        entities = classification["entities"]
        
        # Handle different intents
        if intent == "add_income":
            amount = entities.get("amount", 0)
            return f"✅ आय दर्ज की गई: ₹{amount:,.2f}\n\nधन्यवाद! 🙏"
        
        elif intent == "add_expense":
            amount = entities.get("amount", 0)
            return f"✅ खर्च दर्ज किया गया: ₹{amount:,.2f}\n\nधन्यवाद! 🙏"
        
        elif intent == "add_udhari":
            amount = entities.get("amount", 0)
            party = entities.get("party_name", "ग्राहक")
            return f"✅ उधारी दर्ज की गई:\n{party}: ₹{amount:,.2f}\n\nधन्यवाद! 🙏"
        
        else:
            # Get quick stats for personalized help
            transactions = filter_collection("transactions", {"merchant_id": merchant_id})
            udhari_list = filter_collection("udhari", {"merchant_id": merchant_id, "status": "pending"})
            
            total_transactions = len(transactions)
            total_udhari = len(udhari_list)
            
            help_msg = """नमस्ते! 🙏 मैं Arthsetu Merchant Help हूं, आपका बिज़नेस असिस्टेंट।

🎯 मैं क्या कर सकता हूं:

📊 व्यापार की जानकारी:
• "aaj ka hisaab" - आज का पूरा हिसाब
• "udhari list" - बाकी उधारी की लिस्ट
• "GST status" - GST फाइलिंग स्थिति
• "forecast" - अगले महीने का अनुमान

💰 लेन-देन रिकॉर्ड करें:
• "5000 रुपये आय मिली"
• "2000 खर्च किया"
• "राम को 3000 उधारी दी"

🎤 वॉइस नोट भी भेज सकते हैं!
📸 इनवॉइस की फोटो भी भेज सकते हैं!

"""
            
            # Add personalized stats
            if total_transactions > 0:
                help_msg += f"📈 आपके {total_transactions} लेन-देन रिकॉर्ड हैं\n"
            
            if total_udhari > 0:
                help_msg += f"⚠️ {total_udhari} उधारी बाकी हैं\n"
            
            help_msg += "\n💬 कुछ भी पूछें, मैं मदद करूंगा!"
            
            return help_msg


async def handle_voice_note(media_url: str, merchant_id: str, state: Dict[str, Any]) -> str:
    """
    Handle voice note from WhatsApp
    
    Args:
        media_url: URL of voice note
        merchant_id: Merchant ID
        state: Conversation state
        
    Returns:
        Response text
    """
    try:
        # Download audio from Twilio (requires authentication)
        import httpx
        from app.munim.config import get_munim_config
        
        config = get_munim_config()
        
        # Twilio media URLs require authentication
        auth = (config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        
        # Create client with redirect following enabled
        async with httpx.AsyncClient(follow_redirects=True) as client:
            print(f"[WhatsApp] Downloading voice note from: {media_url}")
            response = await client.get(media_url, auth=auth, timeout=30.0)
            response.raise_for_status()
            audio_data = response.content
            print(f"[WhatsApp] Downloaded {len(audio_data)} bytes of audio")
        
        # Detect audio format from content type or URL
        content_type = response.headers.get("content-type", "")
        if "ogg" in content_type or media_url.endswith(".ogg"):
            filename = "voice_note.ogg"
        elif "mp3" in content_type or media_url.endswith(".mp3"):
            filename = "voice_note.mp3"
        elif "wav" in content_type or media_url.endswith(".wav"):
            filename = "voice_note.wav"
        else:
            # Default to ogg (WhatsApp typically uses ogg)
            filename = "voice_note.ogg"
        
        print(f"[WhatsApp] Transcribing audio as {filename}")
        
        # Transcribe using NLU engine
        nlu_engine = get_nlu_engine()
        transcription = await nlu_engine.transcribe_audio(audio_data, filename)
        
        print(f"[WhatsApp] Transcription: {transcription}")
        
        if not transcription or transcription.strip() == "":
            return "माफ़ करें, मैं वॉइस नोट को समझ नहीं पाया। कृपया फिर से कोशिश करें या टेक्स्ट में लिखें।"
        
        # Process transcribed text as command
        response = await handle_text_command(transcription, merchant_id, state)
        
        return f"🎤 सुना: \"{transcription}\"\n\n{response}"
    
    except httpx.HTTPStatusError as e:
        print(f"[WhatsApp] HTTP error downloading voice note: {e.response.status_code} - {e.response.text}")
        return "माफ़ करें, वॉइस नोट डाउनलोड करने में समस्या हुई। कृपया फिर से कोशिश करें।"
    
    except Exception as e:
        print(f"[WhatsApp] Voice note processing error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return "माफ़ करें, वॉइस नोट को समझने में समस्या हुई। कृपया फिर से कोशिश करें।"


async def handle_invoice_photo(media_url: str, merchant_id: str, state: Dict[str, Any]) -> str:
    """
    Handle invoice photo from WhatsApp
    
    Args:
        media_url: URL of invoice photo
        merchant_id: Merchant ID
        state: Conversation state
        
    Returns:
        Response text
    """
    # TODO: Implement OCR using Groq Vision or similar
    # For now, return placeholder
    return """📸 इनवॉइस फोटो प्राप्त हुई!

OCR फीचर जल्द आ रहा है। अभी के लिए, कृपया मैन्युअली डिटेल्स भेजें:

"5000 रुपये आय मिली राम से" 💬"""


@router.get("/messages/{merchant_id}")
async def get_whatsapp_messages(merchant_id: str, limit: int = 50):
    """
    Get WhatsApp message history for merchant
    
    Args:
        merchant_id: Merchant ID
        limit: Maximum messages to return
        
    Returns:
        List of messages
    """
    messages = filter_collection("whatsapp_messages", {"merchant_id": merchant_id})
    
    # Sort by created_at descending
    messages.sort(key=lambda m: m.get("created_at", ""), reverse=True)
    
    return {
        "messages": messages[:limit],
        "total": len(messages)
    }


@router.get("/conversation/{phone}")
async def get_conversation_state(phone: str):
    """
    Get conversation state for a phone number
    
    Args:
        phone: Phone number
        
    Returns:
        Conversation state
    """
    state = CONVERSATION_STATE.get(phone, {})
    
    return {
        "phone": phone,
        "state": state,
        "has_state": phone in CONVERSATION_STATE
    }
