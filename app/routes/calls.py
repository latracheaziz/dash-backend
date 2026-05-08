import os
import shutil
import uuid
import json
from pathlib import Path
from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional

from app.database import SessionLocal
from app.deps import get_db, get_current_user, require_super_admin
from app.models.user import User
from app.models.call_record import CallRecord
from app.schemas.call_record import CallRecordCreate, CallRecordOut
from app.services.call_service import create_call_record, get_calls_by_user, get_calls_by_employee, get_all_calls, get_dashboard_stats
from app.services.stt_service import speech_to_text, STTError
from app.services.llm_service import analyze_text, LLMError

router = APIRouter(prefix="/calls", tags=["Calls Analytics"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

def process_audio_background(temp_path: Path, call_record_id: int, duration: str):
    db: Session = SessionLocal()
    try:
        print(f"[Monolith] Background operating STT on {temp_path}...")
        transcript = speech_to_text(str(temp_path))
        print(f"[Monolith] Background STT Complete. '{transcript[:50]}...'")
        
        print("[Monolith] Background operating LLM generation...")
        eval_data = analyze_text(transcript)
        
        print(f"[Monolith] Updating DB for call {call_record_id}...")
        record = db.query(CallRecord).filter(CallRecord.id == call_record_id).first()
        if record:
            record.status      = "Completed"
            record.transcript  = eval_data.get("clean_transcript", transcript)
            record.rating      = int(eval_data.get("rating", 3))
            record.explanation = eval_data.get("explanation", "")
            record.strengths   = json.dumps(eval_data.get("strengths",   []))
            record.weaknesses  = json.dumps(eval_data.get("weaknesses",  []))
            record.suggestions = json.dumps(eval_data.get("suggestions", []))
            # NLP pre-classification results
            record.sentiment   = eval_data.get("sentiment", "neutral")
            record.intent      = eval_data.get("intent",    "other")
            record.priority    = eval_data.get("priority",  "medium")
            db.commit()
    except Exception as e:
        print(f"[Monolith Background Error] {e}")
        record = db.query(CallRecord).filter(CallRecord.id == call_record_id).first()
        if record:
            record.status = "Failed"
            db.commit()
    finally:
        db.close()
        # Clean up temp files silently
        try:
            if temp_path.exists():
                os.remove(temp_path)
            wav_path = temp_path.with_suffix(".wav")
            if wav_path.exists():
                os.remove(wav_path)
        except OSError:
            pass


@router.post("/analyze", response_model=CallRecordOut, summary="Analyze audio file natively and store AI evaluation")
async def analyze_call(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    employee_id: Optional[int] = Form(None),
    visitor_name: Optional[str] = Form("Unknown"),
    duration: Optional[str] = Form("0m 0s"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Saves the call record as Pending and kicks off STT + LLM process natively in the background.
    """
    ext = Path(file.filename).suffix if file.filename else ".wav"
    temp_filename = f"{uuid.uuid4().hex}{ext}"
    temp_path = UPLOAD_DIR / temp_filename

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")
        
    try:
        # Create empty "Pending" record
        record_create = CallRecordCreate(
            employee_id=employee_id,
            visitor_name=visitor_name,
            duration=duration,
            status="Pending",
            transcript="",
            rating=0,
            explanation="",
            strengths=[],
            weaknesses=[],
            suggestions=[],
            # NLP fields initialised as empty; set by background task on completion
            sentiment="neutral",
            intent="other",
            priority="medium",
        )
        
        call_record = create_call_record(db, current_user.id, record_create)
        
        # Dispatch background task natively inside FastAPI using ThreadPool
        background_tasks.add_task(process_audio_background, temp_path, call_record["id"], duration)
        
        return dict(call_record)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Analysis Error: {e}")

@router.get("/history/me", summary="Get current user's call history")
def get_my_calls(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_calls_by_user(db, current_user.id)


@router.get("/history/employee/{employee_id}", summary="Get calls evaluated against a specific employee")
def get_employee_calls(employee_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_calls_by_employee(db, employee_id)

@router.get("/history/all", summary="Get all calls globally (Admin)")
def get_global_calls(db: Session = Depends(get_db), current_user: User = Depends(require_super_admin)):
    return get_all_calls(db)

@router.get("/dashboard/stats", summary="Get dynamic statistics for the Analytics Page")
def get_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_dashboard_stats(db, current_user.role, current_user.id)

# IMPORTANT: /{call_id} must be LAST — FastAPI matches routes top-to-bottom.
# Any specific /history/... route defined after this would be shadowed.
@router.get("/{call_id}", response_model=CallRecordOut, summary="Get details for a specific call")
def get_call_details(call_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.services.call_service import parse_call_record
    call = db.query(CallRecord).filter(CallRecord.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")
    return parse_call_record(call)
