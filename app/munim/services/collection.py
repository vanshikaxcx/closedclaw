"""
Udhari Collection Service
Handles debt collection with risk scoring and reminder management
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
import random


class CollectionService:
    """Manages udhari collection with risk scoring"""
    
    def calculate_risk_score(self, udhari: Dict[str, Any]) -> int:
        """
        Calculate risk score (0-100) for an udhari entry
        Higher score = higher risk
        """
        score = 0
        
        # Factor 1: Overdue days (max 40 points)
        due_date = datetime.fromisoformat(udhari.get("due_date", datetime.utcnow().isoformat()))
        days_overdue = (datetime.utcnow() - due_date).days
        if days_overdue > 0:
            score += min(days_overdue * 2, 40)
        
        # Factor 2: Amount (max 30 points)
        amount = udhari.get("amount", 0)
        if amount > 50000:
            score += 30
        elif amount > 20000:
            score += 20
        elif amount > 10000:
            score += 10
        
        # Factor 3: Previous reminders (max 20 points)
        reminders_sent = udhari.get("reminders_sent", 0)
        score += min(reminders_sent * 5, 20)
        
        # Factor 4: Payment history (max 10 points)
        # If debtor has history of late payments
        payment_history = udhari.get("payment_history", "good")
        if payment_history == "poor":
            score += 10
        elif payment_history == "fair":
            score += 5
        
        return min(score, 100)
    
    def get_severity_badge(self, risk_score: int) -> str:
        """Get severity badge based on risk score"""
        if risk_score >= 67:
            return "high"
        elif risk_score >= 34:
            return "medium"
        else:
            return "low"
    
    def select_reminder_channel(self, udhari: Dict[str, Any], risk_score: int) -> str:
        """
        Select optimal reminder channel based on risk score
        Escalation: WhatsApp → SMS → Voice Call
        """
        reminders_sent = udhari.get("reminders_sent", 0)
        
        if reminders_sent == 0:
            return "whatsapp"
        elif reminders_sent == 1:
            return "sms"
        elif reminders_sent >= 2:
            return "voice_call"
        else:
            return "whatsapp"
    
    def generate_reminder_message(self, udhari: Dict[str, Any], channel: str) -> str:
        """
        Generate culturally-aware Hindi reminder message
        Compliant with RBI Fair Practices Code
        """
        debtor_name = udhari.get("debtor_name", "")
        amount = udhari.get("amount", 0)
        due_date = udhari.get("due_date", "")
        
        # Polite and respectful messages
        if channel == "whatsapp":
            message = f"""नमस्ते {debtor_name} जी,

यह एक विनम्र अनुस्मारक है कि ₹{amount} की राशि {due_date} तक देय है।

कृपया जल्द से जल्द भुगतान करें। यदि कोई समस्या है, तो कृपया हमसे संपर्क करें।

धन्यवाद"""
        
        elif channel == "sms":
            message = f"नमस्ते {debtor_name} जी, ₹{amount} की राशि देय है। कृपया भुगतान करें। धन्यवाद।"
        
        else:  # voice_call
            message = f"नमस्ते {debtor_name} जी, यह एक अनुस्मारक है कि ₹{amount} की राशि देय है।"
        
        return message
    
    def can_send_reminder(self, udhari: Dict[str, Any]) -> bool:
        """
        Check if reminder can be sent (24-hour interval enforcement)
        """
        last_reminder = udhari.get("last_reminder_at")
        if not last_reminder:
            return True
        
        last_reminder_time = datetime.fromisoformat(last_reminder)
        hours_since_last = (datetime.utcnow() - last_reminder_time).total_seconds() / 3600
        
        return hours_since_last >= 24
    
    def update_collection_stats(self, udhari: Dict[str, Any], success: bool) -> Dict[str, Any]:
        """
        Update collection statistics after payment/reminder
        Simplified version without Thompson Sampling
        """
        stats = {
            "udhari_id": udhari.get("id"),
            "success": success,
            "channel_used": udhari.get("last_channel_used", "whatsapp"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return stats


# Singleton instance
_collection_service = None

def get_collection_service() -> CollectionService:
    """Get collection service singleton"""
    global _collection_service
    if _collection_service is None:
        _collection_service = CollectionService()
    return _collection_service
