from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from typing import List

from app.database import get_db
from app.models.models import Poll, PollOption
from app.schemas.polls import Poll as PollSchema, PollCreate, VoteRequest

router = APIRouter(prefix="/api/polls", tags=["Polls"])

@router.get("/", response_model=List[PollSchema])
def get_polls(db: Session = Depends(get_db)):
    """Fetch all active polls."""
    return db.query(Poll).filter(Poll.is_active == True).all()

@router.post("/", response_model=PollSchema)
def create_poll(poll: PollCreate, db: Session = Depends(get_db)):
    """Create a new poll (Admin only - simplification)."""
    db_poll = Poll(
        question=poll.question,
        description=poll.description,
        is_active=poll.is_active,
        expires_at=poll.expires_at
    )
    db.add(db_poll)
    db.commit()
    db.refresh(db_poll)
    
    for opt in poll.options:
        db_opt = PollOption(poll_id=db_poll.id, option_text=opt.option_text)
        db.add(db_opt)
    
    db.commit()
    db.refresh(db_poll)
    return db_poll

@router.post("/{poll_id}/vote")
def vote_poll(poll_id: int, vote: VoteRequest, db: Session = Depends(get_db)):
    """Submit a vote for a poll option."""
    opt = db.query(PollOption).filter(PollOption.id == vote.option_id, PollOption.poll_id == poll_id).first()
    if not opt:
        raise HTTPException(status_code=404, detail="Option not found")
    
    opt.votes_count += 1
    db.commit()
    return {"status": "success", "message": "Vote recorded"}

@router.get("/{poll_id}", response_model=PollSchema)
def get_poll(poll_id: int, db: Session = Depends(get_db)):
    """Fetch a single poll with results."""
    poll = db.query(Poll).get(poll_id)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return poll
