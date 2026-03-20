"""Academic Monitoring API - upload, persist, and analyze class risk."""

import io
import json
import os
import re
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from groq import Groq
from sqlalchemy import select
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
    is_excel = filename.endswith((".xlsx", ".xls", ".xlss"))
    is_csv = filename.endswith(".csv")

    if not (is_excel or is_csv):
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file format. Please upload a CSV (.csv) or Excel (.xlsx) file."
        )

    try:
        if is_csv:
            # Handle CSV
            frame = pd.read_csv(io.BytesIO(content))
        else:
            # Handle Excel - added 'openpyxl' engine explicitly
            frame = pd.read_excel(io.BytesIO(content), engine="openpyxl")
    except Exception as e:
        # Provide more detail for the "Zip file" error
        error_msg = str(e)
        if "File is not a zip file" in error_msg:
            error_msg = "Excel parsing failed. If this is a CSV file, please save it correctly as .csv or a real .xlsx workbook."
        raise HTTPException(status_code=400, detail="Invalid file: {0}".format(error_msg))

    if frame.empty:
        raise HTTPException(status_code=400, detail="File is empty.")

    cols = list(frame.columns)
    # Flexible column detection
    student_id_col = _find_col(cols, ["student_id", "student id", "roll", "roll no", "id"])
    name_col = _find_col(cols, ["name", "student name", "student_name"])
    email_col = _find_col(cols, ["email", "email_id", "email id"])
    course_col = _find_col(cols, ["course", "program", "dept"])
    semester_col = _find_col(cols, ["semester", "sem"])
    subject_col = _find_col(cols, ["subject", "subject_name", "subject name"])
    attendance_col = _find_col(cols, ["attendance", "att", "presence"])
    mid_col = _find_col(cols, ["mid_sem", "mid sem", "midsem", "cia3"])
    end_col = _find_col(cols, ["end_sem", "end sem", "endsem", "final"])
    cia_cols = _detect_cia_cols(cols)

    if not student_id_col:
        raise HTTPException(status_code=400, detail="Missing ID column (student_id or roll).")

    # Default subject if missing to prevent crash
    if not subject_col:
        subject_default = "General Academic"
    else:
        subject_default = None

    students_created = 0
    students_updated = 0
    records_created = 0
    records_updated = 0

    for _, row in frame.iterrows():
        student_id = _safe_str(row.get(student_id_col, ""))
        if not student_id:
            continue

        query = await db.execute(select(Student).where(Student.student_id == student_id))
        student = query.scalar_one_or_none()
        
        if student is None:
            student = Student(
                student_id=student_id,
                name=_safe_str(row.get(name_col, "")) or "Student " + student_id,
                email=_safe_str(row.get(email_col, "")),
                course=_safe_str(row.get(course_col, "")),
                semester=_safe_str(row.get(semester_col, "")),
            )
            db.add(student)
            await db.flush()
            students_created += 1
        else:
            if name_col: student.name = _safe_str(row.get(name_col, "")) or student.name
            if email_col: student.email = _safe_str(row.get(email_col, "")) or student.email
            students_updated += 1

        subject_name = _safe_str(row.get(subject_col, "")) if subject_col else subject_default
        if not subject_name:
            continue

        cia_scores = []
        for cia_col in cia_cols:
            score = _safe_float(row.get(cia_col))
            if score is not None:
                cia_scores.append(score)

        record_query = await db.execute(
            select(AcademicRecord).where(
                AcademicRecord.student_pk == student.id,
                AcademicRecord.subject_name == subject_name,
            )
        )
        record = record_query.scalar_one_or_none()
        
        if record is None:
            record = AcademicRecord(
                student_pk=student.id,
                subject_name=subject_name,
                attendance=_safe_float(row.get(attendance_col)) if attendance_col else 0.0,
                cia_scores=cia_scores or [],
                mid_sem=_safe_float(row.get(mid_col)),
                end_sem=_safe_float(row.get(end_col)),
            )
            db.add(record)
            records_created += 1
        else:
            if attendance_col: record.attendance = _safe_float(row.get(attendance_col)) or record.attendance
            if cia_scores: record.cia_scores = cia_scores
            if mid_col: record.mid_sem = _safe_float(row.get(mid_col)) or record.mid_sem
            if end_col: record.end_sem = _safe_float(row.get(end_col)) or record.end_sem
            records_updated += 1

    await db.commit()
    return {
        "status": "success",
        "counts": {
            "students_created": students_created,
            "students_updated": students_updated,
            "records_created": records_created,
            "records_updated": records_updated,
        }
    }

# --- Rest of your analyze_class and helper functions remains the same ---
# (I am keeping the logic intact to save your context/time)

def _build_analysis_payload(rows: List[Dict[str, Any]]) -> str:
    return json.dumps(rows, indent=2)

def _normalize_risk(item: Dict[str, Any]) -> Dict[str, Any]:
    level = str(item.get("risk_level", "Low"))
    normalized = level.upper()
    if normalized.startswith("H"): level = "High"
    elif normalized.startswith("M"): level = "Medium"
    else: level = "Low"
    return {
        "student_id": str(item.get("student_id", "")),
        "risk_level": level,
        "recovery_plan": str(item.get("recovery_plan", "")),
        "email_content": str(item.get("email_content", "")),
    }

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
            "subject_name": record.subject_name,
            "attendance": record.attendance,
            "cia_scores": record.cia_scores or [],
            "mid_sem": record.mid_sem,
            "end_sem": record.end_sem,
        })

    api_key = _get_groq_api_key()
    if not api_key:
        return {"students": rows, "analysis": [], "message": "GROQ_API_KEY missing."}

    prompt = (
        "Identify students at risk based on attendance (<75%) or low scores. "
        "Return JSON only: [{{student_id, risk_level, recovery_plan, email_content}}]. "
        "Data: {0}"
    ).format(_build_analysis_payload(rows))

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Return ONLY a JSON array."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content or "[]"
        analysis_raw = json.loads(content)
        analysis = [_normalize_risk(i) for i in analysis_raw if isinstance(i, dict)]
    except Exception as e:
        msg = str(e)
        if "Connection error" in msg:
            msg = "Connection error to Groq API. Check internet/VPN/firewall and verify GROQ_API_KEY has no extra spaces."
        return {"students": rows, "analysis": [], "message": f"AI Error: {msg}"}

    # Update DB with risk status
    student_map = {s.student_id: s for s, _ in joined}
    for item in analysis:
        student_obj = student_map.get(item["student_id"])
        if student_obj:
            recs_result = await db.execute(select(AcademicRecord).where(AcademicRecord.student_pk == student_obj.id))
            for rec in recs_result.scalars().all():
                rec.risk_status = item["risk_level"]
                rec.recovery_plan = item["recovery_plan"]
                rec.email_content = item["email_content"]
    
    await db.commit()
    return {"students": rows, "analysis": analysis}