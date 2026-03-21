"""Academic AI Agent - Final Inclusive Version: Robust Upload, AI Personas, and Live SMTP."""

import io
import json
import smtplib
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from groq import Groq
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.academic import AcademicRecord, Student

router = APIRouter(prefix="/academic", tags=["academic"])
GROQ_MODEL = "llama-3.3-70b-versatile"

# --- 1. ROBUST UTILITIES ---

def _get_groq_api_key() -> str:
    """Resolve and sanitize GROQ key from settings."""
    return (settings.GROQ_API_KEY or "").strip()

def _normalize_col(col: str) -> str:
    return str(col).strip().lower().replace(" ", "_").replace("-", "_")

def _find_col(columns: List[str], aliases: List[str]) -> Optional[str]:
    normalized = {_normalize_col(c): c for c in columns}
    for alias in aliases:
        key = _normalize_col(alias)
        if key in normalized:
            return normalized[key]
    return None

def _safe_float(value: Any) -> float:
    if pd.isna(value) or value in ("", None):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def _safe_str(value: Any) -> str:
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip()

# --- 2. ENDPOINTS ---

@router.post("/upload-data")
async def upload_data(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    filename = file.filename.lower()
    content = await file.read()
    
    try:
        if filename.endswith(".csv"):
            frame = pd.read_csv(io.BytesIO(content))
        else:
            frame = pd.read_excel(io.BytesIO(content), engine="openpyxl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File error: {str(e)}")

    if frame.empty:
        raise HTTPException(status_code=400, detail="File is empty.")

    # Fresh Start: Clear old records
    await db.execute(delete(AcademicRecord))
    await db.execute(delete(Student))
    await db.commit()

    cols = list(frame.columns)
    student_id_col = _find_col(cols, ["student_id", "roll", "id"])
    name_col = _find_col(cols, ["name", "student_name"])
    email_col = _find_col(cols, ["email"])
    attendance_col = _find_col(cols, ["attendance", "att"])
    subject_col = _find_col(cols, ["subject"])

    if not student_id_col:
        raise HTTPException(status_code=400, detail="Could not find student ID/Roll column.")

    for _, row in frame.iterrows():
        sid = _safe_str(row.get(student_id_col))
        if not sid: continue

        student = Student(
            student_id=sid,
            name=_safe_str(row.get(name_col)) or f"Student {sid}",
            email=_safe_str(row.get(email_col)),
            course=_safe_str(row.get("course", "N/A")),
            semester=_safe_str(row.get("semester", "N/A"))
        )
        db.add(student)
        await db.flush()

        db.add(AcademicRecord(
            student_pk=student.id,
            attendance=_safe_float(row.get(attendance_col)),
            subject_name=_safe_str(row.get(subject_col, "Core")),
            cia_scores=[] 
        ))
    
    await db.commit()
    return {"status": "success", "message": "Import complete."}

@router.get("/analyze-class")
async def analyze_class(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Student, AcademicRecord).join(AcademicRecord))
    joined_data = res.all()
    
    rows_for_ai = []
    for s, r in joined_data:
        rows_for_ai.append({
            "student_id": s.student_id, 
            "name": s.name, 
            "attendance": r.attendance,
            "email": s.email
        })

    api_key = _get_groq_api_key()
    if not api_key:
        return {"students": rows_for_ai, "analysis": [], "error": "No API Key"}

    prompt = (
        "You are an Academic AI Agent. Analyze these students:\n"
        "1. Identify a 'persona' (e.g. 'Hidden Gem', 'Struggling Specialist').\n"
        "2. Risk Level: 'High' (if att < 75), 'Medium', or 'Low'.\n"
        "3. Recovery Plan: 1-sentence actionable advice.\n"
        "4. Email Content: 3-sentence professional intervention email.\n"
        f"Data: {json.dumps(rows_for_ai)}\n"
        "Return ONLY a JSON array of objects with keys: student_id, risk_level, persona, recovery_plan, email_content."
    )

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "system", "content": "Return ONLY valid JSON array."}, {"role": "user", "content": prompt}],
        temperature=0.2
    )
    
    analysis_results = json.loads(response.choices[0].message.content)

    for item in analysis_results:
        for s, r in joined_data:
            if s.student_id == item["student_id"]:
                r.risk_status = item["risk_level"]
                r.recovery_plan = f"[{item.get('persona', 'N/A')}] {item.get('recovery_plan', '')}"
                r.email_content = item["email_content"]
    
    await db.commit()
    return {"students": rows_for_ai, "analysis": analysis_results}

@router.post("/send-interventions")
async def send_interventions(db: AsyncSession = Depends(get_db)):
    """The Agent Action: Actually sends emails using Settings-mapped SMTP credentials."""
    res = await db.execute(
        select(Student, AcademicRecord)
        .join(AcademicRecord)
        .where(AcademicRecord.risk_status.in_(["High", "Medium"]))
    )
    targets = res.all()
    
    # PULLED FROM CONFIG.PY SETTINGS
    user = settings.smtp_user
    pw = settings.smtp_pass

    if not user or not pw:
        print("⚠️ MAILMAN: No SMTP credentials in config. Simulating.")
        return {"status": "simulated", "emails_sent": len(targets)}

    sent_count = 0
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(user, pw)

            for student, record in targets:
                if record.email_content and student.email:
                    msg = MIMEText(record.email_content)
                    msg['Subject'] = f"Academic Support Alert | {student.name}"
                    msg['From'] = f"Atlas AI Agent <{user}>"
                    msg['To'] = student.email
                    
                    server.send_message(msg)
                    sent_count += 1
            
        return {"status": "success", "emails_sent": sent_count}

    except Exception as e:
        print(f"❌ MAILMAN ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Mail Server Error: {str(e)}")