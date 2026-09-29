from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Meeting, Employee, User
from app.schemas import MeetingCreate, MeetingSummaryRequest, MeetingResponse
from app.security import get_current_user
from app.services.meeting_summarizer import summarize_meeting_notes

router = APIRouter(prefix="/meetings", tags=["Meeting Management"])

def _format_meeting(m: Meeting) -> MeetingResponse:
    org_name = f"{m.organizer.first_name} {m.organizer.last_name}" if m.organizer else "Unknown"
    return MeetingResponse(
        id=m.id,
        title=m.title,
        organizer_id=m.organizer_id,
        organizer_name=org_name,
        scheduled_time=m.scheduled_time,
        duration_mins=m.duration_mins,
        attendees=m.attendees or [],
        raw_notes=m.raw_notes,
        ai_summary=m.ai_summary,
        ai_action_items=m.ai_action_items or [],
        created_at=m.created_at
    )

@router.get("/", response_model=List[MeetingResponse])
def list_meetings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    meetings = db.query(Meeting).order_by(Meeting.scheduled_time.desc()).all()
    return [_format_meeting(m) for m in meetings]

@router.post("/", response_model=MeetingResponse)
def schedule_meeting(
    meeting_in: MeetingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    meeting = Meeting(
        title=meeting_in.title,
        organizer_id=meeting_in.organizer_id,
        scheduled_time=meeting_in.scheduled_time,
        duration_mins=meeting_in.duration_mins,
        attendees=meeting_in.attendees,
        raw_notes=meeting_in.raw_notes
    )
    
    if meeting_in.raw_notes:
        summary_obj = summarize_meeting_notes(meeting_in.title, meeting_in.raw_notes)
        meeting.ai_summary = summary_obj.get("summary", "")
        meeting.ai_action_items = summary_obj.get("action_items", [])

    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return _format_meeting(meeting)

@router.post("/{meeting_id}/summarize", response_model=MeetingResponse)
def summarize_existing_meeting(
    meeting_id: int,
    req: MeetingSummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    meeting.raw_notes = req.raw_notes
    summary_obj = summarize_meeting_notes(meeting.title, req.raw_notes)
    meeting.ai_summary = summary_obj.get("summary", "")
    meeting.ai_action_items = summary_obj.get("action_items", [])

    db.commit()
    db.refresh(meeting)
    return _format_meeting(meeting)
