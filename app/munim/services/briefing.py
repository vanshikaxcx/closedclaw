"""
Daily Briefing Service - Generate and send daily morning briefings
"""
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from app.munim.config import get_munim_config
from app.munim.data.mock_store import filter_collection, get_collection
from app.munim.services.twilio_service import get_twilio_service

config = get_munim_config()


class BriefingService:
    """Handles daily briefing generation and delivery"""
    
    def __init__(self):
        self.twilio_service = get_twilio_service()
    
    def generate_briefing_text(self, merchant_id: str) -> str:
        """
        Generate daily briefing text with P&L summary and PayScore
        
        Args:
            merchant_id: Merchant ID
            
        Returns:
            Briefing text in Hindi/English
        """
        # Get today's transactions
        today = datetime.utcnow().date()
        transactions = filter_collection("transactions", {"merchant_id": merchant_id})
        
        # Filter today's transactions
        today_transactions = [
            t for t in transactions 
            if datetime.fromisoformat(t.get("created_at", "")).date() == today
        ]
        
        # Calculate P&L
        income = sum(t["amount"] for t in today_transactions if t["type"] == "income")
        expense = sum(t["amount"] for t in today_transactions if t["type"] == "expense")
        profit = income - expense
        
        # Get udhari summary
        udhari_list = filter_collection("udhari", {"merchant_id": merchant_id, "status": "pending"})
        total_udhari = sum(u["amount"] for u in udhari_list)
        
        # Calculate yesterday's comparison
        yesterday = today - timedelta(days=1)
        yesterday_transactions = [
            t for t in transactions 
            if datetime.fromisoformat(t.get("created_at", "")).date() == yesterday
        ]
        yesterday_income = sum(t["amount"] for t in yesterday_transactions if t["type"] == "income")
        
        # Calculate week's total
        week_start = today - timedelta(days=today.weekday())
        week_transactions = [
            t for t in transactions 
            if datetime.fromisoformat(t.get("created_at", "")).date() >= week_start
        ]
        week_income = sum(t["amount"] for t in week_transactions if t["type"] == "income")
        week_expense = sum(t["amount"] for t in week_transactions if t["type"] == "expense")
        week_profit = week_income - week_expense
        
        # Mock PayScore (in real implementation, fetch from payscore service)
        payscore = 75
        
        # Get day of week in Hindi
        days_hindi = ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"]
        day_name = days_hindi[today.weekday()]
        
        # Generate greeting based on time
        hour = datetime.utcnow().hour
        if hour < 12:
            greeting = "🌅 सुप्रभात"
        elif hour < 17:
            greeting = "☀️ नमस्ते"
        else:
            greeting = "🌙 शुभ संध्या"
        
        # Generate performance message
        if income > yesterday_income:
            performance = f"📈 बढ़िया! कल से {((income - yesterday_income) / max(yesterday_income, 1) * 100):.0f}% ज्यादा आय"
        elif income < yesterday_income and yesterday_income > 0:
            performance = f"📉 कल से {((yesterday_income - income) / yesterday_income * 100):.0f}% कम आय"
        else:
            performance = "💪 आज नया दिन, नई शुरुआत!"
        
        # Generate udhari message
        if len(udhari_list) > 0:
            high_risk = [u for u in udhari_list if u.get("risk_score", 0) > 66]
            if high_risk:
                udhari_msg = f"⚠️ {len(high_risk)} उधारी हाई रिस्क में हैं"
            else:
                udhari_msg = f"✅ सभी उधारी कंट्रोल में हैं"
        else:
            udhari_msg = "🎉 कोई बाकी उधारी नहीं!"
        
        # Generate PayScore message
        if payscore >= 80:
            score_msg = "🌟 बेहतरीन! लोन के लिए योग्य"
        elif payscore >= 60:
            score_msg = "👍 अच्छा स्कोर, और बेहतर बना सकते हैं"
        else:
            score_msg = "💡 स्कोर बढ़ाने के लिए नियमित लेन-देन करें"
        
        # Generate briefing
        briefing = f"""{greeting}! {day_name} का हिसाब:

📊 आज का लेन-देन:
• आय: ₹{income:,.2f}
• खर्च: ₹{expense:,.2f}
• लाभ: ₹{profit:,.2f}

{performance}

� इस हफ्ते अब तक:
• कुल आय: ₹{week_income:,.2f}
• कुल लाभ: ₹{week_profit:,.2f}

💰 उधारी स्थिति:
• बाकी: ₹{total_udhari:,.2f} ({len(udhari_list)} लोग)
• {udhari_msg}

⭐ PayScore: {payscore}/100
{score_msg}

🎯 आज का लक्ष्य: ₹{max(yesterday_income * 1.1, 10000):,.0f} आय

शुभ दिन! 🙏"""
        
        return briefing
    
    async def generate_voice_briefing(self, text: str) -> Optional[bytes]:
        """
        Generate Hindi voice note using Sarvam TTS
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Audio bytes or None if failed
        """
        if not config.SARVAM_API_KEY:
            print("[Briefing] Sarvam API not configured, skipping voice generation")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sarvam.ai/text-to-speech",
                    headers={
                        "Authorization": f"Bearer {config.SARVAM_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": text,
                        "language": "hi-IN",
                        "speaker": "meera",  # Female Hindi voice
                        "pitch": 0,
                        "pace": 1.0,
                        "loudness": 1.5
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.content
                else:
                    print(f"[Briefing] Sarvam TTS failed: {response.status_code} - {response.text}")
                    return None
        
        except Exception as e:
            print(f"[Briefing] Voice generation error: {e}")
            return None
    
    async def send_daily_briefing(self, merchant_id: str, phone: str) -> Dict[str, Any]:
        """
        Send daily briefing to merchant via WhatsApp
        
        Args:
            merchant_id: Merchant ID
            phone: WhatsApp phone number
            
        Returns:
            Result dict with success status
        """
        # Generate briefing text
        briefing_text = self.generate_briefing_text(merchant_id)
        
        # Send text briefing via WhatsApp
        result = self.twilio_service.send_whatsapp(phone, briefing_text)
        
        if not result["success"]:
            return {
                "success": False,
                "error": result["error"],
                "text_sent": False,
                "voice_sent": False
            }
        
        # Try to generate and send voice note (optional)
        voice_sent = False
        try:
            voice_audio = await self.generate_voice_briefing(briefing_text)
            if voice_audio:
                # Note: Twilio WhatsApp doesn't support direct audio upload via API
                # In production, you'd upload to a CDN and send the URL
                # For now, we'll just log that voice was generated
                print(f"[Briefing] Voice note generated ({len(voice_audio)} bytes)")
                voice_sent = True
        except Exception as e:
            print(f"[Briefing] Voice note generation failed: {e}")
        
        return {
            "success": True,
            "text_sent": True,
            "voice_sent": voice_sent,
            "sid": result["sid"],
            "briefing_text": briefing_text
        }
    
    async def send_briefings_to_all_merchants(self) -> Dict[str, Any]:
        """
        Send daily briefings to all merchants
        
        Returns:
            Summary of briefings sent
        """
        # Get all unique merchants from transactions
        transactions = get_collection("transactions")
        merchant_ids = set(t["merchant_id"] for t in transactions)
        
        results = {
            "total_merchants": len(merchant_ids),
            "sent": 0,
            "failed": 0,
            "details": []
        }
        
        for merchant_id in merchant_ids:
            # In real implementation, fetch merchant phone from database
            # For demo, use override phone
            phone = "+919425129512"
            
            try:
                result = await self.send_daily_briefing(merchant_id, phone)
                if result["success"]:
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                
                results["details"].append({
                    "merchant_id": merchant_id,
                    "success": result["success"],
                    "error": result.get("error")
                })
            
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "merchant_id": merchant_id,
                    "success": False,
                    "error": str(e)
                })
        
        return results


# Singleton instance
_briefing_service = None

def get_briefing_service() -> BriefingService:
    """Get briefing service singleton"""
    global _briefing_service
    if _briefing_service is None:
        _briefing_service = BriefingService()
    return _briefing_service
