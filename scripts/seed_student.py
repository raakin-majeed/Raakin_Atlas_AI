
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.user import User, UserRole, UserStatus
from app.models.student import StudentProfile
from app.core.database import Base

async def seed():
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        # Create tables if not exist
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Check if user 1 exists
        from sqlalchemy import select
        user = await session.get(User, 1)
        if not user:
            user = User(
                id=1,
                email="student1@atlas.local",
                hashed_password="hashed_dummy_password",
                role=UserRole.USER,
                status=UserStatus.APPROVED,
                is_active=True
            )
            session.add(user)
            await session.commit()
            print("Created user 1")
        else:
            print("User 1 already exists")

        # Check if student profile 1 exists
        profile = await session.execute(select(StudentProfile).where(StudentProfile.user_id == 1))
        profile = profile.scalar_one_or_none()
        
        if not profile:
            profile = StudentProfile(
                user_id=1,
                attendance_percentage=72.5,
                subject_scores={
                    "DSA": 45,
                    "Math": 38,
                    "DBMS": 62,
                    "OS": 55
                }
            )
            session.add(profile)
            await session.commit()
            print("Created student profile for user 1")
        else:
            print("Student profile for user 1 already exists")

if __name__ == "__main__":
    asyncio.run(seed())
