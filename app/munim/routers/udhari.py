"""
Udhari (Credit/Debt) Management Router
Handles udhari tracking and collection reminders
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.munim.data.mock_store import (
    add_to_collection, 
    get_collection, 
    filter_collection,
    update_in_collection
)
from app.munim.services.collection import get_collection_service
from app.munim.services.twilio_service import get_twilio_service
from app.munim.config import get_munim_config

router = APIRouter()
config = get_munim_config()


class UdhariCreate(BaseModel):
    """Create udhari request"""
    merchant_id: str = "demo_merchant"
    debtor_name: str
    debtor_phone: str
    amount: float
    due_date: str
    description: Optional[str] = None


class UdhariResponse(BaseModel):
    """Udhari response"""
    id: str
    merchant_id: str
    debtor_name: str
    debtor_phone: str
    amount: float
    due_date: str
    risk_score: int
    severity: str
    status: str
    reminders_sent: int
    created_at: str


@router.post("/api/munim/udhari", response_model=UdhariResponse)
async def create_udhari(udhari: UdhariCreate):
    """
    Create a new udhari entry
    """
    try:
        collection_service = get_collection_service()
        
        # Create udhari record
        udhari_record = {
            "id": str(uuid.uuid4()),
            "merchant_id": udhari.merchant_id,
            "debtor_name": udhari.debtor_name,
            "debtor_phone": udhari.debtor_phone,
            "amount": udhari.amount,
            "due_date": udhari.due_date,
            "description": udhari.description,
            "status": "pending",
            "reminders_sent": 0,
            "payment_history": "good",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Calculate risk score
        risk_score = collection_service.calculate_risk_score(udhari_record)
        udhari_record["risk_score"] = risk_score
        udhari_record["severity"] = collection_service.get_severity_badge(risk_score)
        
        # Save to mock store
        add_to_collection("udhari", udhari_record)
        
        return UdhariResponse(**udhari_record)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create udhari: {str(e)}")


@router.get("/api/munim/udhari")
async def get_udhari_list(
    merchant_id: str = "demo_merchant",
    status: Optional[str] = None  # pending, paid, overdue
):
    """
    Get list of udhari entries for a merchant
    """
    try:
        # Get all udhari for merchant
        all_udhari = filter_collection("udhari", {"merchant_id": merchant_id})
        
        # Filter by status if specified
        if status:
            all_udhari = [u for u in all_udhari if u.get("status") == status]
        
        # Recalculate risk scores
        collection_service = get_collection_service()
        for udhari in all_udhari:
            risk_score = collection_service.calculate_risk_score(udhari)
            udhari["risk_score"] = risk_score
            udhari["severity"] = collection_service.get_severity_badge(risk_score)
        
        # Sort by risk score (highest first)
        all_udhari.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
        
        # Calculate totals
        total_amount = sum(u.get("amount", 0) for u in all_udhari)
        
        return {
            "merchant_id": merchant_id,
            "total_amount": round(total_amount, 2),
            "count": len(all_udhari),
            "udhari_list": all_udhari
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch udhari: {str(e)}")


@router.post("/api/munim/udhari/{udhari_id}/remind")
async def send_reminder(udhari_id: str):
    """
    Send reminder for a specific udhari entry
    """
    try:
        # Get udhari record
        all_udhari = get_collection("udhari")
        udhari = next((u for u in all_udhari if u.get("id") == udhari_id), None)
        
        if not udhari:
            raise HTTPException(status_code=404, detail="Udhari not found")
        
        collection_service = get_collection_service()
        
        # Check if reminder can be sent (24-hour interval)
        if not collection_service.can_send_reminder(udhari):
            raise HTTPException(
                status_code=429, 
                detail="Please wait 24 hours before sending another reminder"
            )
        
        # Calculate risk score
        risk_score = collection_service.calculate_risk_score(udhari)
        
        # Select channel
        channel = collection_service.select_reminder_channel(udhari, risk_score)
        
        # Generate message
        message = collection_service.generate_reminder_message(udhari, channel)
        
        # Send reminder via Twilio
        reminder_sent = False
        twilio_response = {}
        
        if config.is_configured("twilio"):
            twilio_service = get_twilio_service()
            debtor_phone = udhari.get("debtor_phone", "")
            
            if channel == "whatsapp":
                twilio_response = twilio_service.send_whatsapp(debtor_phone, message)
            elif channel == "sms":
                twilio_response = twilio_service.send_sms(debtor_phone, message)
            elif channel == "voice_call":
                twilio_response = twilio_service.make_voice_call(debtor_phone, message)
            
            reminder_sent = twilio_response.get("success", False)
            
            if not reminder_sent:
                print(f"⚠️ Twilio error: {twilio_response.get('error')}")
        else:
            # Mock mode
            print(f"📱 Mock reminder sent via {channel}: {message}")
            reminder_sent = True
        
        # Update udhari record
        updates = {
            "reminders_sent": udhari.get("reminders_sent", 0) + 1,
            "last_reminder_at": datetime.utcnow().isoformat(),
            "last_channel_used": channel
        }
        update_in_collection("udhari", udhari_id, updates)
        
        # Store reminder history
        reminder_record = {
            "id": str(uuid.uuid4()),
            "udhari_id": udhari_id,
            "merchant_id": udhari.get("merchant_id"),
            "channel": channel,
            "message": message,
            "sent": reminder_sent,
            "timestamp": datetime.utcnow().isoformat()
        }
        add_to_collection("collection_history", reminder_record)
        
        return {
            "success": reminder_sent,
            "udhari_id": udhari_id,
            "channel": channel,
            "message": message,
            "timestamp": reminder_record["timestamp"],
            "twilio_sid": twilio_response.get("sid") if config.is_configured("twilio") else None,
            "error": twilio_response.get("error") if config.is_configured("twilio") else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send reminder: {str(e)}")


@router.get("/api/munim/udhari/{udhari_id}/history")
async def get_reminder_history(udhari_id: str):
    """
    Get reminder history for a specific udhari entry
    """
    try:
        # Get reminder history
        all_history = filter_collection("collection_history", {"udhari_id": udhari_id})
        
        # Sort by timestamp (most recent first)
        all_history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return {
            "udhari_id": udhari_id,
            "count": len(all_history),
            "history": all_history
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")


@router.put("/api/munim/udhari/{udhari_id}/mark-paid")
async def mark_udhari_paid(udhari_id: str):
    """
    Mark udhari as paid
    """
    try:
        # Update udhari status
        updates = {
            "status": "paid",
            "paid_at": datetime.utcnow().isoformat()
        }
        result = update_in_collection("udhari", udhari_id, updates)
        
        if not result:
            raise HTTPException(status_code=404, detail="Udhari not found")
        
        return {
            "success": True,
            "udhari_id": udhari_id,
            "status": "paid"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark as paid: {str(e)}")
