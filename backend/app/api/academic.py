"""Academic Monitoring API - upload, persist, and analyze class risk."""

import io
import json
import os
import re
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

def _get_groq_api_key() -> str:
    """Resolve and sanitize GROQ key from settings/env."""
    return (settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")).strip()

def _normalize_col(col: str) -> str:
    return str(col).strip().lower().replace(" ", "_").replace("-", "_")

def _find_col(columns: List[str], aliases: List[str]) -> Optional[str]:
    normalized = {_normalize_col(c): c for c in columns}
    for alias in aliases:
        key = _normalize_col(alias)
        if key in normalized:
            return normalized[key]
    return None

def _detect_cia_cols(columns: List[str]) -> List[str]:
    pattern = re.compile(r"cia[\s_]?(\d+)", re.IGNORECASE)
    found = []
    for col in columns:
        match = pattern.search(_normalize_col(col))
        if match:
            found.append((int(match.group(1)), col))
    return [c for _, c in sorted(found, key=lambda item: item[0])]

def _safe_float(value: Any) -> Optional[float]:
    if pd.isna(value) or value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _safe_str(value: Any) -> str:
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip()

@router.post("/upload-data")
async def upload_data(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    filename = file.filename.lower()
    content = await file.read()
    
    # Supported extensions
    is_excel = filename.endswith((".xlsx", ".xls"))
    is_csv = filename.endswith(".csv")

    if not (is_excel or is_csv):
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file format. Please upload a CSV (.csv) or Excel (.xlsx) file."
        )

    try:
        if is_csv:
            frame = pd.read_csv(io.BytesIO(content))
        else:
            frame = pd.read_excel(io.BytesIO(content), engine="openpyxl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid file: {str(e)}")

    if frame.empty:
        raise HTTPException(status_code=400, detail="File is empty.")

    # --- THE FRESH START: Clear old data for a professional demo session ---
    await db.execute(delete(AcademicRecord))
    await db.execute(delete(Student))
    await db.commit()

    cols = list(frame.columns)
    
    # Flexible column detection
    student_id_col = _find_col(cols, ["student_id", "roll", "id"])
    name_col = _find_col(cols, ["name", "student_name"])
    email_col = _find_col(cols, ["email"])
    course_col = _find_col(cols, ["course", "dept", "program"])
    semester_col = _find_col(cols, ["semester", "sem"])
    attendance_col = _find_col(cols, ["attendance", "att"])
    subject_col = _find_col(cols, ["subject"])

    if not student_id_col:
        raise HTTPException(status_code=400, detail="Missing ID column (student_id or roll).")

    for _, row in frame.iterrows():
        sid = _safe_str(row.get(student_id_col, ""))
        if not sid:
            continue

        # Create new student record with fallbacks to avoid NOT NULL constraints
        student = Student(
            student_id=sid,
            name=_safe_str(row.get(name_col, "")) or f"Student {sid}",
            email=_safe_str(row.get(email_col, "")),
            course=_safe_str(row.get(course_col, "")) or "N/A",
            semester=_safe_str(row.get(semester_col, "")) or "N/A"
        )
        db.add(student)
        await db.flush()

        # Create academic record
        db.add(AcademicRecord(
            student_pk=student.id,
            subject_name=_safe_str(row.get(subject_col, "General Academic")),
            attendance=_safe_float(row.get(attendance_col)) or 0.0,
            cia_scores=[],
        ))

    await db.commit()
    return {"status": "success", "message": "Database cleared and new data imported."}

@router.get("/analyze-class")
async def analyze_class(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    join_result = await db.execute(
        select(Student, AcademicRecord).join(AcademicRecord, AcademicRecord.student_pk == Student.id)
    )
    joined = join_result.all()
    if not joined:
        return {"students": [], "analysis": []}

    rows = []
    for student, record in joined:
        rows.append({
            "student_id": student.student_id,
            "name": student.name,
            "email": student.email,
            "attendance": record.attendance,
        })

    api_key = _get_groq_api_key()
    if not api_key:
        return {"students": rows, "analysis": [], "message": "GROQ_API_KEY missing."}

    # Enhanced prompt for intervention actions
    prompt = (
        "Analyze these students for academic risk. For each student, provide:\n"
        "1. risk_level: 'High' (attendance < 75%), 'Medium', or 'Low'.\n"
        "2. recovery_plan: A brief 1-sentence actionable advice.\n"
        "3. email_content: A professional 3-sentence email draft for student intervention.\n"
        f"Return ONLY a JSON array of objects. Data: {json.dumps(rows)}"
    )

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Return ONLY a JSON array of objects with keys: student_id, risk_level, recovery_plan, email_content."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        
        content = response.choices[0].message.content or "[]"
        analysis = json.loads(content)
        
        # Update DB records with the AI results
        for item in analysis:
            for student, record in joined:
                if student.student_id == item.get("student_id"):
                    record.risk_status = item.get("risk_level", "Low")
                    record.recovery_plan = item.get("recovery_plan", "")
                    record.email_content = item.get("email_content", "")
        
        await db.commit()
        return {"students": rows, "analysis": analysis}
        
    except Exception as e:
        return {"students": rows, "analysis": [], "message": f"AI Error: {str(e)}"}