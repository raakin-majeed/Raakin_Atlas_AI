from logging.config import fileConfig

from sqlalchemy import create_engine
from alembic import context

from app.core.config import settings
from app.core.database import Base
from app.models import User, Agent, AgentTask, AuditLog
from app.models.academic import Student, AcademicRecord  # noqa: F401 - register for SQLModel.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

sync_url = settings.DATABASE_URL.replace("+aiosqlite", "")
# Include both SQLAlchemy Base and SQLModel metadata for migrations
from sqlmodel import SQLModel
target_metadata = [Base.metadata, SQLModel.metadata]


def run_migrations_offline() -> None:
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(sync_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
