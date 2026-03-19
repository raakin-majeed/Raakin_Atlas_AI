from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.student import StudentProfile
from app.schemas.student_schema import StudentProfileCreate, StudentProfileResponse

router = APIRouter(prefix="/students", tags=["students"])


@router.post("", response_model=StudentProfileResponse)
async def create_student_profile(
    body: StudentProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    student = StudentProfile(**body.model_dump())
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return student


@router.get("/{user_id}", response_model=StudentProfileResponse)
async def get_student_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()