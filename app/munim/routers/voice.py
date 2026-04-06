"""
Voice Processing Router
Handles voice command processing and Soundbox integration
"""
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from app.munim.services.nlu import get_nlu_engine
from app.munim.data.mock_store import add_to_collection, get_collection

router = APIRouter()


class VoiceProcessResponse(BaseModel):
    """Response from voice processing"""
    command_id: str
    transcription: str
    intent: str
    confidence: float
    entities: Dict[str, Any]
    timestamp: str


class VoiceTextRequest(BaseModel):
    """Text-based voice command (for testing without audio)"""
    text: str
    merchant_id: str = "demo_merchant"


@router.post("/api/munim/voice/process", response_model=VoiceProcessResponse)
async def process_voice_command(
    audio: UploadFile = File(...),
    merchant_id: str = Form("demo_merchant")
):
    """
    Process voice command from audio file
    Accepts audio blob and returns structured command with intent and entities
    """
    try:
        # Read audio data
        audio_data = await audio.read()
        
        # Get NLU engine
        nlu_engine = get_nlu_engine()
        
        # Process voice command
        result = await nlu_engine.process_voice_command(audio_data, audio.filename)
        
        # Generate command ID
        command_id = str(uuid.uuid4())
        
        # Store in voice commands history
        command_record = {
            "id": command_id,
            "merchant_id": merchant_id,
            "transcription": result["transcription"],
            "intent": result["intent"],
            "confidence": result["confidence"],
            "entities": result["entities"],
            "timestamp": datetime.utcnow().isoformat(),
            "audio_filename": audio.filename
        }
        add_to_collection("voice_commands", command_record)
        
        return VoiceProcessResponse(
            command_id=command_id,
            transcription=result["transcription"],
            intent=result["intent"],
            confidence=result["confidence"],
            entities=result["entities"],
            timestamp=command_record["timestamp"]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(e)}")


@router.post("/api/munim/voice/text", response_model=VoiceProcessResponse)
async def process_text_command(request: VoiceTextRequest):
    """
    Process text command (for testing without audio)
    Useful for development and testing
    """
    try:
        # Get NLU engine
        nlu_engine = get_nlu_engine()
        
        # Classify intent and extract entities
        classification = await nlu_engine.classify_intent(request.text)
        
        # Generate command ID
        command_id = str(uuid.uuid4())
        
        # Store in voice commands history
        command_record = {
            "id": command_id,
            "merchant_id": request.merchant_id,
            "transcription": request.text,
            "intent": classification["intent"],
            "confidence": classification["confidence"],
            "entities": classification["entities"],
            "timestamp": datetime.utcnow().isoformat(),
            "audio_filename": None
        }
        add_to_collection("voice_commands", command_record)
        
        return VoiceProcessResponse(
            command_id=command_id,
            transcription=request.text,
            intent=classification["intent"],
            confidence=classification["confidence"],
            entities=classification["entities"],
            timestamp=command_record["timestamp"]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text processing failed: {str(e)}")


@router.get("/api/munim/voice/history")
async def get_voice_history(merchant_id: str = "demo_merchant", limit: int = 50):
    """
    Get voice command history for a merchant
    """
    try:
        # Get all voice commands
        all_commands = get_collection("voice_commands")
        
        # Filter by merchant
        merchant_commands = [
            cmd for cmd in all_commands 
            if cmd.get("merchant_id") == merchant_id
        ]
        
        # Sort by timestamp (most recent first)
        merchant_commands.sort(
            key=lambda x: x.get("timestamp", ""), 
            reverse=True
        )
        
        # Limit results
        return {
            "merchant_id": merchant_id,
            "total": len(merchant_commands),
            "commands": merchant_commands[:limit]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")


@router.get("/api/munim/voice/stats")
async def get_voice_stats(merchant_id: str = "demo_merchant"):
    """
    Get voice command statistics for a merchant
    """
    try:
        # Get all voice commands for merchant
        all_commands = get_collection("voice_commands")
        merchant_commands = [
            cmd for cmd in all_commands 
            if cmd.get("merchant_id") == merchant_id
        ]
        
        # Calculate stats
        total_commands = len(merchant_commands)
        
        # Intent distribution
        intent_counts = {}
        for cmd in merchant_commands:
            intent = cmd.get("intent", "unknown")
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        # Average confidence
        confidences = [cmd.get("confidence", 0) for cmd in merchant_commands]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "merchant_id": merchant_id,
            "total_commands": total_commands,
            "intent_distribution": intent_counts,
            "average_confidence": round(avg_confidence, 2)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")
