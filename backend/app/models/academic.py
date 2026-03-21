"""Academic Monitoring models."""

from typing import List, Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship, SQLModel


class Student(SQLModel, table=True):
    __tablename__ = "academic_students"

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: str = Field(index=True, unique=True)
    name: str
    email: str = Field(index=True)
    course: str
    semester: str

    records: List["AcademicRecord"] = Relationship(back_populates="student")


class AcademicRecord(SQLModel, table=True):
    __tablename__ = "academic_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    student_pk: int = Field(foreign_key="academic_students.id", index=True)
    subject_name: str
    attendance: Optional[float] = None
    cia_scores: Optional[List[float]] = Field(default=None, sa_column=Column(JSON))
    average_score: Optional[float] = None
    trend: Optional[float] = None
    ai_generated_analysis: Optional[str] = None
    mid_sem: Optional[float] = None
    end_sem: Optional[float] = None
    risk_status: Optional[str] = None
    recovery_plan: Optional[str] = None
    email_content: Optional[str] = None

    student: Optional[Student] = Relationship(back_populates="records")
