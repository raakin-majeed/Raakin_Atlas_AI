from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.agent import AgentStatus, TaskStatus


class AgentRegisterRequest(BaseModel):
    name: str
    module_type: str


class AgentResponse(BaseModel):
    id: int
    name: str
    module_type: str
    status: AgentStatus
    last_heartbeat: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class HeartbeatResponse(BaseModel):
    status: str = "ok"


class TaskLogRequest(BaseModel):
    task_description: str
    status: TaskStatus = TaskStatus.RUNNING
    execution_time: Optional[float] = None
