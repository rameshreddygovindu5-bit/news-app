"""Polls API — public voting + admin management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List

from app.database import get_db
from app.models.models import Poll, PollOption, AdminUser
from app.schemas.polls import Poll as PollSchema, PollCreate, VoteRequest
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/polls", tags=["Polls"])


@router.get("/", response_model=List[PollSchema])
async def get_polls(db: AsyncSession = Depends(get_db)):
    """Fetch all active polls (public endpoint)."""
    result = await db.execute(
        select(Poll).where(Poll.is_active == True).order_by(Poll.created_at.desc())
    )
    polls = result.scalars().all()
    # Eagerly load options
    for poll in polls:
        opts_result = await db.execute(
            select(PollOption).where(PollOption.poll_id == poll.id)
        )
        poll.options = opts_result.scalars().all()
    return polls


@router.post("/", response_model=PollSchema)
async def create_poll(
    poll: PollCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """Create a new poll (admin only)."""
    db_poll = Poll(
        question=poll.question,
        description=poll.description,
        is_active=poll.is_active,
        expires_at=poll.expires_at,
    )
    db.add(db_poll)
    await db.commit()
    await db.refresh(db_poll)

    for opt in poll.options:
        db_opt = PollOption(poll_id=db_poll.id, option_text=opt.option_text)
        db.add(db_opt)

    await db.commit()
    await db.refresh(db_poll)
    # Load options
    opts_result = await db.execute(
        select(PollOption).where(PollOption.poll_id == db_poll.id)
    )
    db_poll.options = opts_result.scalars().all()
    return db_poll


@router.post("/{poll_id}/vote")
async def vote_poll(
    poll_id: int,
    vote: VoteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit a vote for a poll option (public endpoint)."""
    result = await db.execute(
        select(PollOption).where(
            PollOption.id == vote.option_id,
            PollOption.poll_id == poll_id,
        )
    )
    opt = result.scalar_one_or_none()
    if not opt:
        raise HTTPException(status_code=404, detail="Option not found")

    opt.votes_count = (opt.votes_count or 0) + 1
    await db.commit()
    return {"status": "success", "message": "Vote recorded"}


@router.get("/{poll_id}", response_model=PollSchema)
async def get_poll(poll_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch a single poll with results."""
    result = await db.execute(select(Poll).where(Poll.id == poll_id))
    poll = result.scalar_one_or_none()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    opts_result = await db.execute(
        select(PollOption).where(PollOption.poll_id == poll.id)
    )
    poll.options = opts_result.scalars().all()
    return poll
