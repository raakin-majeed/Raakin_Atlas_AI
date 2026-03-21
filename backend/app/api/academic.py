"""Academic counselor view API."""

import io
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.academic import AcademicRecord, Student
from app.services.intervention_service import (
    analyze_with_groq,
    calculate_average_and_trend,
    ensure_academic_columns,
    safe_float,
    send_intervention,
)

router = APIRouter(prefix="/academic", tags=["academic"])
logger = logging.getLogger(__name__)


def _normalize_col(col: str) -> str:
    s = str(col).strip().lstrip("\ufeff").strip('"').strip("'")
    return s.lower().replace(" ", "_").replace("-", "_")


def _clean_frame_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Strip BOM/quotes from header names (common CSV export issue)."""
    frame = frame.copy()
    frame.columns = [
        str(c).strip().lstrip("\ufeff").strip('"').strip("'") for c in frame.columns
    ]
    return frame


def _is_probably_xlsx(content: bytes) -> bool:
    """.xlsx is a ZIP file (PK\\x03\\x04)."""
    return len(content) >= 4 and content[:2] == b"PK"


def _load_upload_table(content: bytes, filename: str) -> pd.DataFrame:
    """
    Pick CSV vs Excel from extension and magic bytes so unnamed / wrong-extension uploads still work.
    """
    name = (filename or "").lower()
    buf = io.BytesIO(content)

    def read_csv_enc(enc: str) -> pd.DataFrame:
        buf.seek(0)
        return pd.read_csv(buf, encoding=enc)

    if name.endswith(".csv"):
        try:
            return read_csv_enc("utf-8-sig")
        except UnicodeDecodeError:
            buf.seek(0)
            return pd.read_csv(buf, encoding="latin-1")

    if name.endswith(".xlsx") or name.endswith(".xls"):
        buf.seek(0)
        return pd.read_excel(buf, engine="openpyxl")

    # No / unknown extension (e.g. "blob", "") — sniff content
    if _is_probably_xlsx(content):
        buf.seek(0)
        return pd.read_excel(buf, engine="openpyxl")

    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            buf.seek(0)
            return pd.read_csv(buf, encoding=enc)
        except (UnicodeDecodeError, pd.errors.EmptyDataError):
            continue
        except Exception:
            # Wrong encoding or not CSV — try next encoding, then Excel below
            continue

    buf.seek(0)
    try:
        return pd.read_excel(buf, engine="openpyxl")
    except Exception as e:
        raise ValueError(
            "Could not read file as CSV or Excel. Try saving as .csv (UTF-8) or .xlsx. Detail: {0}".format(str(e))
        ) from e


def _find_col(columns: List[str], aliases: List[str]) -> Optional[str]:
    normalized = {_normalize_col(c): c for c in columns}
    for alias in aliases:
        key = _normalize_col(alias)
        if key in normalized:
            return normalized[key]
    return None


def _safe_str(value: Any) -> str:
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip()


@router.post("/upload-data")
async def upload_data(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Counselor schema expected:
    Student_Name, Email, Subject, CIA_1, CIA_2, Attendance
    """
    await ensure_academic_columns(db)
    content = await file.read()

    try:
        frame = _load_upload_table(content, file.filename or "")
        frame = _clean_frame_columns(frame)
    except ValueError as e:
        logger.warning("upload-data rejected: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.warning("upload-data file error: %s", e)
        raise HTTPException(status_code=400, detail="File error: {0}".format(str(e)))

    if frame.empty:
        logger.warning("upload-data rejected: empty file")
        raise HTTPException(status_code=400, detail="File is empty.")

    await db.execute(delete(AcademicRecord))
    await db.execute(delete(Student))
    await db.commit()

    cols = list(frame.columns)
    name_col = _find_col(
        cols,
        ["Student_Name", "Name", "name", "Student Name", "Full Name", "Student", "Learner"],
    )
    email_col = _find_col(
        cols,
        ["Email", "email", "E-mail", "E_mail", "Student Email", "Mail", "Email Address"],
    )
    subject_col = _find_col(
        cols,
        ["Subject", "subject", "Course", "Module", "Subject Name", "Course Name", "Class"],
    )
    cia1_col = _find_col(
        cols,
        ["CIA_1", "CIA1", "cia1", "CIA 1", "Internal 1", "Test 1", "Int 1", "I1"],
    )
    cia2_col = _find_col(
        cols,
        ["CIA_2", "CIA2", "cia2", "CIA 2", "Internal 2", "Test 2", "Int 2", "I2"],
    )
    attendance_col = _find_col(
        cols,
        [
            "Attendance",
            "attendance",
            "Attendance %",
            "Attendance%",
            "Presence",
            "Att",
            "Att %",
            "Attendance_Percent",
        ],
    )
    mid_sem_col = _find_col(
        cols,
        ["mid_sem", "Mid Sem", "Mid-Sem", "MidSem", "Mid Semester", "MidSemester"],
    )
    student_id_col = _find_col(
        cols,
        ["student_id", "Student_ID", "Student ID", "ID", "Roll No", "RollNo"],
    )

    required = [
        ("Name", name_col),
        ("Email", email_col),
    ]
    missing = [label for label, col in required if not col]
    if missing:
        detail = "Missing column(s): {0}. Detected columns: {1}".format(
            ", ".join(missing),
            ", ".join(repr(c) for c in cols[:25]) + ("..." if len(cols) > 25 else ""),
        )
        logger.warning("upload-data rejected: %s", detail)
        raise HTTPException(status_code=400, detail=detail)

    subject_default = "General"
    row_index = 0
    seen_students: Dict[str, Student] = {}

    for _, row in frame.iterrows():
        row_index += 1
        student_name = _safe_str(row.get(name_col) if name_col else "")
        email = _safe_str(row.get(email_col) if email_col else "")
        subject_name = _safe_str(row.get(subject_col)) if subject_col else subject_default
        cia_1 = safe_float(row.get(cia1_col)) if cia1_col else None
        cia_2 = safe_float(row.get(cia2_col)) if cia2_col else None
        attendance_val = safe_float(row.get(attendance_col)) if attendance_col else None
        mid_sem_val = safe_float(row.get(mid_sem_col)) if mid_sem_col else None

        if not student_name:
            continue

        # Multi-subject: one Student per student_id, new AcademicRecord per subject row.
        if student_id_col:
            raw_id = _safe_str(row.get(student_id_col))
            student_id = raw_id if raw_id else f"row_{row_index}"
        else:
            base = (email.split("@")[0] if email and "@" in email else student_name.replace(" ", "_")).strip()
            student_id = f"{base}_{row_index}"

        if student_id not in seen_students:
            student = Student(
                student_id=student_id,
                name=student_name,
                email=email or f"{student_id}@unknown",
                course="Counselor View",
                semester="N/A",
            )
            db.add(student)
            await db.flush()
            seen_students[student_id] = student
        student = seen_students[student_id]

        average_score, trend = calculate_average_and_trend(cia_1, cia_2)

        record = AcademicRecord(
            student_pk=student.id,
            subject_name=subject_name or subject_default,
            attendance=attendance_val,
            cia_scores=[x for x in [cia_1, cia_2] if x is not None],
            average_score=average_score,
            trend=trend,
            mid_sem=mid_sem_val,
            end_sem=None,
            ai_generated_analysis="",
        )
        db.add(record)

    await db.commit()
    return {"status": "success", "message": "Counselor dataset imported."}


def _risk_order(level: str) -> int:
    """Higher = worse. For 'worst' risk across subjects."""
    return {"High": 3, "Medium": 2, "Moderate": 2, "Low": 1}.get(level, 0)


@router.get("/analyze-class")
async def analyze_class(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    await ensure_academic_columns(db)
    res = await db.execute(select(Student, AcademicRecord).join(AcademicRecord, AcademicRecord.student_pk == Student.id))
    joined_data = res.all()

    # Group by student_id
    by_student: Dict[str, List[tuple]] = defaultdict(list)
    for student, record in joined_data:
        by_student[student.student_id].append((student, record))

    for student_id, pairs in by_student.items():
        student = pairs[0][0]
        records = [r for _, r in pairs]

        subject_performances: List[Dict[str, Any]] = []
        attendances: List[float] = []
        failing_subjects: List[str] = []

        low_attendance_subjects: List[str] = []
        for record in records:
            subj = record.subject_name or "General"
            avg = float(record.average_score) if record.average_score is not None else None
            trend = float(record.trend) if record.trend is not None else None
            att = record.attendance
            if att is not None:
                attendances.append(float(att))
                if float(att) < 75:
                    low_attendance_subjects.append(subj)

            subject_performances.append({
                "subject": subj,
                "average": avg,
                "trend": trend,
                "attendance": float(att) if att is not None else None,
            })
            if avg is not None and avg < 50:
                failing_subjects.append(subj)

        # Build subject-aware payload for AI
        avg_att_val = round(sum(attendances) / len(attendances), 2) if attendances else None
        payload = {
            "student_id": student.student_id,
            "student_name": student.name,
            "email": student.email,
            "subject_performances": subject_performances,
            "failing_subjects": failing_subjects,
            "low_attendance_subjects": list(dict.fromkeys(low_attendance_subjects)),
            "average_attendance": avg_att_val,
        }

        print(f"Analyzing {student.name}...")
        ai = None
        try:
            ai = await analyze_with_groq(payload)
        except Exception as e:
            print(f"AI error for {student.name}: {e}")

        risk = "Low"
        recovery = ""
        email_content = ""
        analysis_text = "Pending"
        if ai and isinstance(ai, dict):
            risk = ai.get("risk_level") or "Low"
            recovery = str(ai.get("recovery_plan") or "")
            email_content = str(ai.get("email_content") or "")
            at = ai.get("analysis")
            analysis_text = str(at) if at not in (None, "") else "Pending"

        for record in records:
            record.risk_status = risk
            record.recovery_plan = recovery
            record.email_content = email_content
            record.ai_generated_analysis = analysis_text
            db.add(record)
        print(f"Done {student.name}")

    await db.commit()

    for _, record in joined_data:
        await db.refresh(record)

    students: List[Dict[str, Any]] = []
    analysis: List[Dict[str, Any]] = []
    for student_id, pairs in by_student.items():
        student = pairs[0][0]
        records = [r for _, r in pairs]
        attendances = [float(r.attendance) for r in records if r.attendance is not None]
        failing = list(dict.fromkeys(r.subject_name for r in records if r.average_score is not None and float(r.average_score) < 50))
        low_att = list(dict.fromkeys(r.subject_name for r in records if r.attendance is not None and float(r.attendance) < 75))
        risks = [r.risk_status for r in records if r.risk_status]
        overall = max(risks, key=_risk_order) if risks else "Low"
        avg_att = round(sum(attendances) / len(attendances), 2) if attendances else None

        students.append({
            "student_id": student.student_id,
            "student_name": student.name,
            "email": student.email,
            "subjects_enrolled": len(records),
            "failing_subjects": failing,
            "low_attendance_subjects": low_att,
            "average_attendance": avg_att,
        })
        rec = records[0]
        analysis.append({
            "student_id": student.student_id,
            "risk_level": overall,
            "analysis": rec.ai_generated_analysis or "Pending",
            "recovery_plan": rec.recovery_plan or "",
            "email_content": rec.email_content or "",
        })

    return {"students": students, "analysis": analysis}


@router.get("/counselor-view")
async def counselor_view(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    await ensure_academic_columns(db)
    res = await db.execute(select(Student, AcademicRecord).join(AcademicRecord, AcademicRecord.student_pk == Student.id))
    data = []
    for student, record in res.all():
        data.append(
            {
                "student_id": student.student_id,
                "student_name": student.name,
                "email": student.email,
                "subject": record.subject_name,
                "attendance": record.attendance,
                "average_score": record.average_score,
                "trend": record.trend,
                "ai_generated_analysis": record.ai_generated_analysis,
                "risk_status": record.risk_status,
            }
        )
    return {"data": data}


def _should_send_intervention(records: List[AcademicRecord], avg_att: Optional[float]) -> bool:
    """Include if risk is High/Medium/Moderate OR overall attendance < 75%."""
    has_risk = any(r.risk_status in ("High", "Medium", "Moderate") for r in records if r.risk_status)
    att_below_75 = avg_att is not None and float(avg_att) < 75
    return has_risk or att_below_75


@router.post("/send-interventions")
async def send_interventions(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    await ensure_academic_columns(db)
    res = await db.execute(
        select(Student, AcademicRecord).join(AcademicRecord, AcademicRecord.student_pk == Student.id)
    )
    rows = res.all()

    # Group by student; compute avg attendance; include if risk OR att < 75%; prioritize att < 75%
    by_student: Dict[str, tuple] = {}
    for student, record in rows:
        if student.student_id not in by_student:
            by_student[student.student_id] = (student, [])
        _, recs = by_student[student.student_id]
        recs.append(record)

    ordered: List[tuple] = []
    for student_id, (student, recs) in by_student.items():
        attendances = [float(r.attendance) for r in recs if r.attendance is not None]
        avg_att = round(sum(attendances) / len(attendances), 2) if attendances else None
        if _should_send_intervention(recs, avg_att):
            ordered.append((student, recs[0], avg_att))  # recs[0] has same email_content for all

    # Prioritize: attendance < 75% first, then by risk
    def _order_key(item: tuple) -> tuple:
        student, record, avg_att = item
        att_first = 0 if (avg_att is not None and float(avg_att) < 75) else 1
        risk = _risk_order(record.risk_status or "Low")
        return (att_first, -risk)

    ordered.sort(key=_order_key)

    seen_students = set()
    sent = 0
    for student, record, avg_att in ordered:
        if student.student_id in seen_students:
            continue
        seen_students.add(student.student_id)
        print(f"Sending to {student.email}...")
        # Use AI-generated email_content from DB; fallback to template if empty
        email_body = (record.email_content or "").strip()
        if not email_body:
            parts = [
                f"Dear {student.name},",
                "",
                "Based on your academic performance review, we wanted to reach out with support.",
            ]
            if avg_att is not None and float(avg_att) < 75:
                x = round(float(avg_att), 1)
                parts.append("")
                parts.append(
                    f"Your current attendance is {x}%, which is below the mandatory 75% requirement. "
                    "You are currently ineligible to appear for the End-Semester examinations. "
                    "We urge you to attend the remaining sessions to bridge this gap."
                )
            if record.recovery_plan and record.recovery_plan.strip():
                parts.append("")
                parts.append("Recommended next steps:")
                parts.append(record.recovery_plan.strip())
            elif record.ai_generated_analysis and record.ai_generated_analysis.strip():
                parts.append("")
                parts.append(record.ai_generated_analysis.strip())
            parts.append("")
            parts.append("Please connect with your counselor to discuss further.")
            email_body = "\n".join(parts)

        if send_intervention(
            to_email=student.email,
            student_name=student.name,
            email_body=email_body,
        ):
            sent += 1

    return {"status": "success", "emails_sent": sent, "smtp_user": settings.smtp_user}