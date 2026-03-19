from datetime import datetime, timezone
from sqlalchemy import Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    attendance_percentage: Mapped[float] = mapped_column(Float, default=0.0)

    # Example: {"DSA": 65, "Math": 40, "DBMS": 75}
    subject_scores: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Optional: trend tracking
    last_updated: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )