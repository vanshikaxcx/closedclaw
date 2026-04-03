from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
try:
    import google.generativeai as genai  # type: ignore
except Exception:
    genai = None

try:
    from groq import Groq  # type: ignore
except Exception:
    Groq = None

try:
    from mistralai.client import Mistral  # type: ignore
except Exception:
    Mistral = None


from app.audit import write_entry
from app.database import DatabaseClient, utc_now_iso
from app.dependencies import get_firestore_db

try:
    import edge_tts  # type: ignore
except Exception:
    edge_tts = None

try:
    import fitz  # type: ignore
except Exception:
    fitz = None

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=False)

router = APIRouter()


class VoiceTextRequest(BaseModel):
    query: str
    merchant_id: str = "default_user"
    generate_audio: bool = True


_mistral_client: Mistral | None = None
_groq_client: Groq | None = None
_gemini_configured = False
_gemini_ocr_model: Any | None = None
_gemini_voice_model: Any | None = None


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} is not configured")
    return value


def _get_mistral_client() -> Mistral:
    global _mistral_client
    if Mistral is None:
        raise ValueError("mistralai SDK is not installed")
    if _mistral_client is None:
        _mistral_client = Mistral(api_key=_require_env("MISTRAL_API_KEY"))
    return _mistral_client


def _get_groq_client() -> Groq:
    global _groq_client
    if Groq is None:
        raise ValueError("groq SDK is not installed")
    if _groq_client is None:
        _groq_client = Groq(api_key=_require_env("GROQ_API_KEY"))
    return _groq_client


def _get_gemini_models() -> tuple[Any, Any]:
    global _gemini_configured
    global _gemini_ocr_model
    global _gemini_voice_model

    if genai is None:
        raise ValueError("google-generativeai SDK is not installed")

    api_key = _require_env("GEMINI_API_KEY")
    if not _gemini_configured:
        genai.configure(api_key=api_key)
        _gemini_configured = True

    if _gemini_ocr_model is None:
        _gemini_ocr_model = genai.GenerativeModel("gemini-2.5-flash")
    if _gemini_voice_model is None:
        _gemini_voice_model = genai.GenerativeModel("gemini-2.0-flash")

    return _gemini_ocr_model, _gemini_voice_model


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if not text:
        raise ValueError("empty Gemini response")

    fenced = re.search(r"```json\s*(\{.*\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)

    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or start >= end:
        raise ValueError("Gemini did not return JSON")

    payload = json.loads(text[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("Gemini JSON response is not an object")
    return payload


def _strip_code_fences(raw_text: str) -> str:
    text = raw_text.strip()
    text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^```", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def _run_mistral_ocr(image_bytes: bytes, mime_type: str) -> str:
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    client = _get_mistral_client()

    response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "image_url",
            "image_url": f"data:{mime_type};base64,{base64_image}",
        },
    )

    pages = getattr(response, "pages", None)
    if pages and len(pages) > 0:
        first_page = pages[0]
        if isinstance(first_page, dict):
            markdown = str(first_page.get("markdown") or first_page.get("text") or "").strip()
        else:
            markdown = str(getattr(first_page, "markdown", "") or getattr(first_page, "text", "")).strip()
        if markdown:
            return markdown

    if isinstance(response, dict):
        fallback_text = str(response.get("text") or "").strip()
        if fallback_text:
            return fallback_text

    raise ValueError("OCR extraction returned empty text")


def _gemini_safety_settings() -> dict[Any, Any]:
    return {
        genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
        genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
    }


def _structure_with_gemini(ocr_text: str) -> dict[str, Any]:
    ocr_model, _ = _get_gemini_models()

    prompt = (
        "You are an Indian GST bill parser. Extract data into strict JSON format.\n"
        f"Raw OCR Text: {ocr_text}\n"
        "Required keys: vendor_name, vendor_gstin, items(list), grand_total.\n"
        "Do NOT include markdown fences (```json)."
    )

    response = ocr_model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(temperature=0.1, max_output_tokens=8192),
        safety_settings=_gemini_safety_settings(),
    )

    raw_text = str(getattr(response, "text", "") or "").strip()
    if not raw_text:
        raise ValueError("Gemini structuring returned empty output")

    clean_json = _strip_code_fences(raw_text)
    structured = _extract_json_object(clean_json)

    structured.setdefault("vendor_name", "")
    structured.setdefault("vendor_gstin", "")
    structured.setdefault("items", [])
    structured.setdefault("grand_total", 0)

    if not isinstance(structured.get("items"), list):
        structured["items"] = []

    return structured


def _voice_response_from_gemini(query: str) -> str:
    _, voice_model = _get_gemini_models()

    prompt = f"Act as ArthSetu VoiceBot, an empathetic Indian GST expert. Answer precisely: {query}"
    response = voice_model.generate_content(prompt)
    answer = str(getattr(response, "text", "") or "").strip()
    if not answer:
        raise ValueError("Gemini returned an empty response")
    return answer


def _groq_transcribe(audio_bytes: bytes, filename: str) -> str:
    client = _get_groq_client()
    transcription = client.audio.transcriptions.create(
        file=(filename or "audio.webm", audio_bytes),
        model="whisper-large-v3",
        language="en",
    )

    text = str(getattr(transcription, "text", "") or "").strip()
    if not text and isinstance(transcription, dict):
        text = str(transcription.get("text") or "").strip()

    if not text:
        raise ValueError("Groq transcription returned empty text")

    return text


async def _synthesize_voice(text: str) -> str:
    if edge_tts is None:
        raise ValueError("edge_tts is not installed")

    voice_name = os.environ.get("EDGE_TTS_VOICE", "en-IN-NeerjaNeural").strip() or "en-IN-NeerjaNeural"
    communicate = edge_tts.Communicate(text, voice=voice_name, rate="+5%")

    audio_data = b""
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            audio_data += chunk.get("data", b"")

    if not audio_data:
        raise ValueError("TTS synthesis produced empty audio")

    return base64.b64encode(audio_data).decode("utf-8")


@router.post("/ocr-bill")
async def post_ocr_bill(bill: UploadFile = File(...)):
    file_bytes = await bill.read()
    if not file_bytes:
        return JSONResponse(status_code=422, content={"status": "error", "message": "Uploaded file is empty."})

    filename = (bill.filename or "bill").lower()
    content_type = (bill.content_type or "").lower()

    try:
        if filename.endswith(".pdf") or content_type == "application/pdf":
            if not fitz:
                raise HTTPException(status_code=500, detail="PyMuPDF missing")
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                if doc.page_count < 1:
                    raise HTTPException(status_code=422, detail="Empty PDF uploaded")
                pix = doc.load_page(0).get_pixmap(dpi=200)
                image_bytes = pix.tobytes("jpeg")
                mime_type = "image/jpeg"
        elif filename.endswith((".jpg", ".jpeg")) or content_type in {"image/jpeg", "image/jpg"}:
            image_bytes = file_bytes
            mime_type = "image/jpeg"
        elif filename.endswith(".png") or content_type == "image/png":
            image_bytes = file_bytes
            mime_type = "image/png"
        else:
            return JSONResponse(
                status_code=422,
                content={"status": "error", "message": "Only JPEG, PNG, and PDF are supported."},
            )

        ocr_text = _run_mistral_ocr(image_bytes=image_bytes, mime_type=mime_type)
        structured_data = _structure_with_gemini(ocr_text)
        return {"status": "success", "structured_json": structured_data}
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse(status_code=422, content={"status": "error", "message": str(exc)})


@router.post("/ocr-save")
def post_ocr_save(payload: dict[str, Any], db: DatabaseClient = Depends(get_firestore_db)):
    merchant_id = str(payload.get("merchant_id") or payload.get("merchantId") or "").strip() or "unknown"
    structured = payload.get("structured_json") if isinstance(payload.get("structured_json"), dict) else payload

    try:
        write_entry(
            db,
            actor_type="merchant",
            actor_id=merchant_id,
            action="ocr_result_saved",
            entity_id=merchant_id,
            outcome="success",
            metadata={"keys": sorted(list(structured.keys())) if isinstance(structured, dict) else []},
        )
    except Exception:
        pass

    return {
        "status": "success",
        "saved": True,
        "saved_at": utc_now_iso(),
    }


@router.post("/gst-voice/audio")
async def post_gst_voice_audio(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=422, detail={"error": "audio file is empty"})

    try:
        transcription = _groq_transcribe(audio_bytes=audio_bytes, filename=audio.filename or "audio.webm")
        response_text = _voice_response_from_gemini(transcription)
        audio_base64 = await _synthesize_voice(response_text)

        return {
            "transcription": transcription,
            "response_text": response_text,
            "audio_base64": audio_base64,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"error": str(exc)}) from exc


@router.post("/gst-voice/text")
async def post_gst_voice_text(body: VoiceTextRequest):
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail={"error": "query is required"})

    try:
        response_text = _voice_response_from_gemini(query)
        payload: dict[str, Any] = {"response_text": response_text}

        if body.generate_audio:
            try:
                payload["audio_base64"] = await _synthesize_voice(response_text)
            except Exception:
                payload["audio_base64"] = None

        return payload
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"error": str(exc)}) from exc
