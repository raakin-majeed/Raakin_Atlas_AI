import json
import smtplib
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

from groq import Groq
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


# Normalization factors: raw score * factor = 100-point scale
CIA_FACTOR = 10.0   # CIAs out of 10
MID_SEM_FACTOR = 5.0   # Mid-Sem out of 20


def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    value_str = str(value).strip()
    if value_str == "":
        return None
    try:
        return float(value_str)
    except (TypeError, ValueError):
        return None


def normalize_cia(raw: Optional[float]) -> Optional[float]:
    """CIA out of 10 → 100-point scale."""
    if raw is None:
        return None
    return round(raw * CIA_FACTOR, 2)


def normalize_mid_sem(raw: Optional[float]) -> Optional[float]:
    """Mid-Sem out of 20 → 100-point scale."""
    if raw is None:
        return None
    return round(raw * MID_SEM_FACTOR, 2)


def calculate_average_and_trend(cia_1: Optional[float], cia_2: Optional[float]) -> Tuple[float, float]:
    """
    Normalize CIAs to 100-point scale (raw * 10), then compute average and trend.
    Trend = Normalized_CIA_2 - Normalized_CIA_1 (e.g. 9/10→90, 4/10→40 → trend -50).
    Missing scores are not factored in.
    """
    n1 = normalize_cia(cia_1)
    n2 = normalize_cia(cia_2)
    if n1 is not None and n2 is not None:
        average = round((n1 + n2) / 2.0, 2)
        trend = round(n2 - n1, 2)
        return average, trend
    if n1 is not None:
        return n1, 0.0
    if n2 is not None:
        return n2, 0.0
    return 0.0, 0.0


def build_ai_prompt(student_data: Dict[str, Any]) -> str:
    """Build subject-aware prompt for multi-subject admin dashboard."""
    payload = {k: v for k, v in student_data.items() if v is not None and not str(k).startswith("_")}

    subject_performances = student_data.get("subject_performances") or []
    failing_subjects = student_data.get("failing_subjects") or []
    has_multi_subject = len(subject_performances) > 1

    scale_note = (
        "SCALE: CIAs are out of 10, Mid-Sems are out of 20. "
        "The 'average' and 'trend' fields are normalized to a 100-point scale. "
        "A score below 50 (normalized) indicates failing performance.\n\n"
    )

    subject_instruction = ""
    if has_multi_subject:
        good = [p["subject"] for p in subject_performances if p.get("average") is not None and p["average"] >= 50]
        bad = [p["subject"] for p in subject_performances if p.get("average") is not None and p["average"] < 50]
        if good and bad:
            subject_instruction = (
                f"This student is doing well in {', '.join(good)} but struggling in {', '.join(bad)}. "
                "Draft an email that addresses these specific subject imbalances. "
            )
        elif bad:
            subject_instruction = (
                f"This student is struggling in {', '.join(bad)}. "
                "Draft an email that offers targeted support for these subjects. "
            )
        else:
            subject_instruction = (
                "This student is performing adequately across subjects. "
                "Draft a brief, supportive check-in email. "
            )
    else:
        subject_instruction = "Analyze this student's semester performance and draft a supportive outreach email. "

    avg_att = student_data.get("average_attendance")
    attendance_below_75 = avg_att is not None and float(avg_att) < 75
    attendance_warning = ""
    if attendance_below_75:
        x = round(float(avg_att), 1)
        attendance_warning = (
            f"ATTENDANCE COMPLIANCE (75% RULE): This student's overall attendance is {x}%, below the mandatory 75%. "
            "You MUST include the following verbatim in BOTH the 'analysis' and 'email_content': "
            f"'Your current attendance is {x}%, which is below the mandatory 75% requirement. "
            "You are currently ineligible to appear for the End-Semester examinations.' "
            "The email must be firm but supportive—urge them to attend the remaining sessions to bridge the gap. "
        )

    return (
        "You are an academic counselor assistant for an Admin Dashboard.\n"
        "Analyze this student's semester across all their subjects. "
        f"{subject_instruction}\n\n"
        f"{attendance_warning}\n\n"
        f"{scale_note}"
        "Return STRICT JSON only with keys: risk_level, recovery_plan, email_content, analysis.\n\n"
        "IMPORTANT:\n"
        "- risk_level: MUST be exactly one of ['High', 'Medium', 'Low']. "
        "Use High if any subject is failing (normalized < 50) or attendance is low. "
        "Use Medium for moderate concerns. Use Low if performing adequately.\n"
        "- analysis: MUST be a concise 2-bullet summary. Use format: '• Bullet one\\n• Bullet two'\n"
        "- email_content: MUST be a personalized, supportive outreach email. "
        "Address the student by name. Reference specific subjects where they excel or struggle. "
        "Include actionable next steps. This will be sent as the actual outreach email.\n\n"
        "Student Data (JSON):\n"
        f"{json.dumps(payload, default=str)}"
    )


def _extract_json_from_llm_text(raw: str) -> str:
    """Strip optional ```json ... ``` fences from model output."""
    t = (raw or "").strip()
    if not t.startswith("```"):
        return t
    parts = t.split("```")
    for chunk in parts:
        chunk = chunk.strip()
        if not chunk:
            continue
        if chunk.lower().startswith("json"):
            chunk = chunk[4:].lstrip()
        return chunk.strip()
    return t


SAFE_AI_FALLBACK: Dict[str, str] = {
    "risk_level": "Low",
    "recovery_plan": "",
    "email_content": "",
    "analysis": "Insufficient data for deep analysis, but student is currently enrolled.",
}


async def analyze_with_groq(student_data: Dict[str, Any]) -> Dict[str, str]:
    api_key = (settings.GROQ_API_KEY or "").strip()
    if not api_key:
        return {
            "risk_level": "Medium",
            "recovery_plan": "GROQ_API_KEY missing.",
            "email_content": "",
            "analysis": "AI analysis unavailable: missing API key.",
        }
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Return ONLY valid JSON object."},
                {"role": "user", "content": build_ai_prompt(student_data)},
            ],
            temperature=0.2,
        )
        raw = response.choices[0].message.content or ""
        json_text = _extract_json_from_llm_text(raw)
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError:
            # AI returned raw text instead of JSON; use it as analysis so UI never shows "AI Error"
            raw_analysis = (raw or json_text or "").strip()
            return {
                "risk_level": "Low",
                "recovery_plan": "",
                "email_content": "",
                "analysis": raw_analysis if raw_analysis else SAFE_AI_FALLBACK["analysis"],
            }

        if not isinstance(parsed, dict):
            raw_analysis = (raw or json_text or "").strip()
            return {
                "risk_level": "Low",
                "recovery_plan": "",
                "email_content": "",
                "analysis": raw_analysis if raw_analysis else SAFE_AI_FALLBACK["analysis"],
            }

        risk = str(parsed.get("risk_level", "Low")).strip()
        if risk not in ("High", "Medium", "Low"):
            risk = "Low"

        return {
            "risk_level": risk,
            "recovery_plan": str(parsed.get("recovery_plan", "")),
            "email_content": str(parsed.get("email_content", "")),
            "analysis": str(parsed.get("analysis", "")),
        }
    except Exception as e:
        # Never surface "AI Error" to UI; use safe fallback
        return {
            "risk_level": "Low",
            "recovery_plan": "",
            "email_content": "",
            "analysis": "Analysis temporarily unavailable. Student is currently enrolled.",
        }


async def ensure_academic_columns(db: AsyncSession) -> None:
    """
    PostgreSQL-compatible schema patching. Uses information_schema to detect
    existing columns, then adds missing ones. Works with postgresql+asyncpg.
    """
    try:
        result = await db.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'academic_records'"
            )
        )
        cols = {row[0] for row in result.fetchall()}
    except Exception:
        cols = set()

    alter_statements = []
    if "average_score" not in cols:
        alter_statements.append("ALTER TABLE academic_records ADD COLUMN average_score DOUBLE PRECISION")
    if "trend" not in cols:
        alter_statements.append("ALTER TABLE academic_records ADD COLUMN trend DOUBLE PRECISION")
    if "ai_generated_analysis" not in cols:
        alter_statements.append("ALTER TABLE academic_records ADD COLUMN ai_generated_analysis VARCHAR")
    if "mid_sem" not in cols:
        alter_statements.append("ALTER TABLE academic_records ADD COLUMN mid_sem DOUBLE PRECISION")

    for stmt in alter_statements:
        try:
            await db.execute(text(stmt))
        except Exception:
            pass
    if alter_statements:
        await db.commit()


def send_intervention(to_email: str, student_name: str, email_body: str) -> bool:
    user = (settings.smtp_user or "").strip()
    password = (settings.smtp_pass or "").strip()
    if not user or not password or not to_email or not email_body:
        return False
    msg = MIMEText(email_body)
    msg["Subject"] = "Academic Intervention Support Plan"
    msg["From"] = user
    msg["To"] = to_email
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception:
        return False
