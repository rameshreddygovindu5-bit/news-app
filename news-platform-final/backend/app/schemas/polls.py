from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PollOptionBase(BaseModel):
    option_text: str

class PollOptionCreate(PollOptionBase):
    pass

class PollOption(PollOptionBase):
    id: int
    poll_id: int
    votes_count: int

    class Config:
        from_attributes = True

class PollBase(BaseModel):
    question: str
    description: Optional[str] = None
    is_active: bool = True
    expires_at: Optional[datetime] = None

class PollCreate(PollBase):
    options: List[PollOptionCreate]

class Poll(PollBase):
    id: int
    created_at: datetime
    options: List[PollOption]

    class Config:
        from_attributes = True

class VoteRequest(BaseModel):
    option_id: int
