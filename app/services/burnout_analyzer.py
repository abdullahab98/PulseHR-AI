from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
import json
import logging
from sqlalchemy.orm import Session

from app.models import (
    Employee, Attendance, AttendanceStatus,
    Task, TaskStatus, TaskPriority,
    LeaveRequest, LeaveStatus, Meeting
)
from app.schemas import BurnoutAnalysisItem, BurnoutSummaryResponse
from app.services.ai_engine import ai_engine
from app.timezone import get_local_now, get_local_today

logger = logging.getLogger(__name__)

def calculate_employee_burnout(employee_id: int, db: Session, use_ai: bool = True) -> BurnoutAnalysisItem:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise ValueError("Employee not found")

    today = get_local_today()
    thirty_days_ago = today - timedelta(days=30)
    sixty_days_ago = today - timedelta(days=60)
    fourteen_days_ago = today - timedelta(days=14)

    # 1. ATTENDANCE & WORK HOURS TELEMETRY (Last 30 Days)
    attendance_records = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.date >= thirty_days_ago
    ).all()

    total_overtime = sum(float(a.overtime_hours or 0) for a in attendance_records)
    late_arrivals = sum(1 for a in attendance_records if a.status == AttendanceStatus.LATE)
    
    # Calculate daily work hours from check_in / check_out if available
    work_durations = []
    weekend_work_days = 0
    for a in attendance_records:
        # Check if record fell on a Friday or Saturday (standard BD weekend)
        if a.date.weekday() in [4, 5] and a.status in [AttendanceStatus.PRESENT, AttendanceStatus.LATE]:
            weekend_work_days += 1
            
        if a.check_in and a.check_out:
            duration = (a.check_out - a.check_in).total_seconds() / 3600.0
            if 0 < duration < 24:
                work_durations.append(duration)

    avg_daily_work_hours = round(sum(work_durations) / max(len(work_durations), 1), 1) if work_durations else 8.0
    if total_overtime > 0 and not work_durations:
        # Approximate if timestamps absent
        avg_daily_work_hours = round(8.0 + (total_overtime / max(len(attendance_records), 1)), 1)

    # 2. TASK ACCUMULATION & DEADLINE PRESSURE
    active_tasks = db.query(Task).filter(
        Task.assignee_id == employee_id,
        Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW])
    ).all()
    pending_tasks_count = len(active_tasks)

    overdue_count = sum(1 for t in active_tasks if t.due_date and t.due_date < today)
    high_priority_count = sum(1 for t in active_tasks if getattr(t, 'priority', None) in [TaskPriority.HIGH, TaskPriority.URGENT])

    completed_tasks_30d = db.query(Task).filter(
        Task.assignee_id == employee_id,
        Task.status == TaskStatus.DONE
    ).count()

    # 3. LEAVE HISTORY & VACATION DEFICIT (Last 60 Days)
    approved_leaves = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee_id,
        LeaveRequest.status == LeaveStatus.APPROVED,
        LeaveRequest.start_date >= sixty_days_ago
    ).order_by(LeaveRequest.end_date.desc()).all()

    leave_days_taken_60d = sum((l.end_date - l.start_date).days + 1 for l in approved_leaves)

    latest_leave = approved_leaves[0] if approved_leaves else None
    if latest_leave and latest_leave.end_date:
        days_since_last_leave = max(0, (today - latest_leave.end_date).days)
    else:
        days_since_last_leave = 75  # Default baseline for no recorded leave in 2+ months

    # 4. MEETING LOAD (Last 14 Days)
    meetings_count = 0
    try:
        meetings_count = db.query(Meeting).filter(
            Meeting.organizer_id == employee.user_id,
            Meeting.scheduled_at >= datetime.combine(fourteen_days_ago, datetime.min.time())
        ).count()
    except Exception:
        meetings_count = 0

    # -------------------------------------------------------------
    # 5. STATISTICAL MULTI-FACTOR BASELINE FORMULA
    # -------------------------------------------------------------
    # OT Factor: Up to 35 pts (Over 25h OT triggers maximum penalty)
    ot_pts = min(total_overtime / 25.0, 1.0) * 35.0

    # Task Pressure: Up to 25 pts (High priority & overdue tasks escalate stress)
    task_pts = min((pending_tasks_count * 2.0 + overdue_count * 5.0 + high_priority_count * 3.0) / 25.0, 1.0) * 25.0

    # Schedule & Rest Deficit: Up to 25 pts (Weekend work + long work hours + zero leave)
    weekend_pts = min(weekend_work_days * 5.0, 10.0)
    leave_pts = 10.0 if leave_days_taken_60d == 0 else max(0.0, (4 - leave_days_taken_60d) * 2.5)
    hours_pts = max(0.0, min((avg_daily_work_hours - 8.0) * 4.0, 10.0))
    rest_pts = min(weekend_pts + leave_pts + hours_pts, 25.0)

    # Late Arrival & Irregularity: Up to 15 pts
    late_pts = min(late_arrivals / 4.0, 1.0) * 15.0

    raw_score = ot_pts + task_pts + rest_pts + late_pts
    baseline_burnout = round(min(max(raw_score, 8.0), 96.0), 1)

    # Work-Life Balance inverse index
    baseline_wlb = round(max(10.0, min(100.0 - (baseline_burnout * 0.9), 95.0)), 1)

    if baseline_burnout >= 80:
        base_risk = "CRITICAL"
        base_status = "Severe Burnout Threat"
        base_fatigue = "Extreme"
        base_retention = "High"
    elif baseline_burnout >= 60:
        base_risk = "HIGH"
        base_status = "High Workload Strain"
        base_fatigue = "Severe"
        base_retention = "Moderate"
    elif baseline_burnout >= 35:
        base_risk = "MEDIUM"
        base_status = "Moderate Work Fatigue"
        base_fatigue = "Moderate"
        base_retention = "Low"
    else:
        base_risk = "LOW"
        base_status = "Balanced & Productive"
        base_fatigue = "Mild"
        base_retention = "Low"

    # Default fallback content
    dept_title = str(employee.department.name if employee.department else "Operations")
    desig_title = str(employee.designation or "Staff Member")

    ai_summary = (
        f"{employee.first_name} exhibits a {base_status.lower()} profile with {total_overtime}h monthly overtime and {pending_tasks_count} active tasks ({overdue_count} overdue). "
        f"Work-life balance is rated at {baseline_wlb}/100 with {days_since_last_leave} days since last extended leave."
    )
    
    key_stressors = []
    if total_overtime > 10:
        key_stressors.append(f"{round(total_overtime, 1)} hrs monthly overtime surge")
    if overdue_count > 0:
        key_stressors.append(f"{overdue_count} overdue milestone task(s)")
    if weekend_work_days > 0:
        key_stressors.append(f"{weekend_work_days} weekend work session(s) logged")
    if leave_days_taken_60d == 0:
        key_stressors.append("Zero approved leave days taken in the last 60 days")
    if late_arrivals >= 3:
        key_stressors.append(f"{late_arrivals} late check-in instances indicating schedule strain")
    if not key_stressors:
        key_stressors = ["Workload within acceptable limits", "Regular check-in cadence"]

    recommendations = [
        f"Schedule a bi-weekly 1-on-1 workload alignment meeting with {employee.first_name}.",
        f"Review deadline feasibility for {overdue_count} overdue deliverable(s).",
        f"Recommend 1-2 days of recharge leave to reset cognitive fatigue."
    ]

    employee_wellness_tips = [
        "Establish a hard daily log-off time to disconnect from work communications.",
        "Implement 5-minute movement breaks every 90 minutes of focused work.",
        "Prioritize the top 3 high-impact tasks each morning and delegate administrative items."
    ]

    # -------------------------------------------------------------
    # 6. ENRICHMENT VIA GEMINI 3.5 FLASH LITE
    # -------------------------------------------------------------
    if use_ai and ai_engine.get_client():
        prompt = (
            f"You are the Chief Occupational Psychologist & AI HR Well-Being Engine for an enterprise software company.\n\n"
            f"Analyze the following real employee biometric & performance telemetry:\n"
            f"- Employee: {employee.first_name} {employee.last_name}\n"
            f"- Role: {desig_title}, Department: {dept_title}\n"
            f"- Overtime in last 30 days: {round(total_overtime, 1)} hours\n"
            f"- Average daily work hours: {avg_daily_work_hours} hours\n"
            f"- Weekend workdays logged: {weekend_work_days}\n"
            f"- Late check-ins: {late_arrivals}\n"
            f"- Active tasks: {pending_tasks_count} (Overdue: {overdue_count}, High Priority: {high_priority_count})\n"
            f"- Completed tasks in 30d: {completed_tasks_30d}\n"
            f"- Leave taken in last 60 days: {leave_days_taken_60d} days (Days since last leave: {days_since_last_leave})\n"
            f"- Meetings attended in 14d: {meetings_count}\n"
            f"- Statistical Baseline Score: {baseline_burnout}/100\n\n"
            f"Respond ONLY in valid JSON matching this exact structure without markdown backticks:\n"
            f"{{\n"
            f'  "burnout_score": number (between 5 and 98),\n'
            f'  "risk_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",\n'
            f'  "health_status": "3-5 words describing mental & fatigue state",\n'
            f'  "work_life_balance_score": number (between 5 and 95),\n'
            f'  "retention_risk": "Low" | "Moderate" | "High" | "Critical",\n'
            f'  "fatigue_level": "Mild" | "Moderate" | "Severe" | "Extreme",\n'
            f'  "ai_summary": "2-3 sentences deep clinical yet empathetic diagnosis",\n'
            f'  "key_stressors": ["stressor 1", "stressor 2", "stressor 3"],\n'
            f'  "recommendations": ["Manager action 1", "Manager action 2", "Manager action 3"],\n'
            f'  "employee_wellness_tips": ["Personal wellness tip 1", "Personal wellness tip 2", "Personal wellness tip 3"]\n'
            f"}}"
        )

        try:
            ai_data = ai_engine.generate_structured_json(
                prompt,
                schema_description="JSON object with burnout_score, risk_level, health_status, work_life_balance_score, retention_risk, fatigue_level, ai_summary, key_stressors, recommendations, employee_wellness_tips"
            )

            if ai_data and isinstance(ai_data, dict):
                baseline_burnout = float(ai_data.get("burnout_score", baseline_burnout))
                base_risk = str(ai_data.get("risk_level", base_risk)).upper()
                base_status = str(ai_data.get("health_status", base_status))
                baseline_wlb = float(ai_data.get("work_life_balance_score", baseline_wlb))
                base_retention = str(ai_data.get("retention_risk", base_retention))
                base_fatigue = str(ai_data.get("fatigue_level", base_fatigue))
                ai_summary = str(ai_data.get("ai_summary", ai_summary))
                if ai_data.get("key_stressors"):
                    key_stressors = [str(s) for s in ai_data.get("key_stressors")]
                if ai_data.get("recommendations"):
                    recommendations = [str(r) for r in ai_data.get("recommendations")]
                if ai_data.get("employee_wellness_tips"):
                    employee_wellness_tips = [str(t) for t in ai_data.get("employee_wellness_tips")]
        except Exception as e:
            logger.warning(f"Gemini 3.5 Flash Lite enrichment fallback used for {employee.id}: {e}")

    now_iso = get_local_now().strftime("%Y-%m-%d %H:%M:%S")

    return BurnoutAnalysisItem(
        employee_id=employee.id,
        employee_name=f"{employee.first_name} {employee.last_name}",
        department_name=dept_title,
        designation=desig_title,
        avatar_url=getattr(employee, 'profile_picture', None),
        burnout_score=round(baseline_burnout, 1),
        risk_level=base_risk,
        health_status=base_status,
        work_life_balance_score=round(baseline_wlb, 1),
        retention_risk=base_retention,
        fatigue_level=base_fatigue,
        overtime_hours_month=round(total_overtime, 1),
        late_arrivals_count=late_arrivals,
        pending_tasks_count=pending_tasks_count,
        overdue_tasks_count=overdue_count,
        high_priority_tasks_count=high_priority_count,
        completed_tasks_30d=completed_tasks_30d,
        leave_days_taken_last_60d=leave_days_taken_60d,
        days_since_last_leave=days_since_last_leave,
        weekend_work_days=weekend_work_days,
        avg_daily_work_hours=avg_daily_work_hours,
        meetings_count_14d=meetings_count,
        ai_summary=ai_summary,
        key_stressors=key_stressors[:5],
        recommendations=recommendations[:4],
        employee_wellness_tips=employee_wellness_tips[:4],
        last_evaluated_at=now_iso
    )

def analyze_company_burnout(db: Session, force_ai: bool = False) -> List[BurnoutAnalysisItem]:
    employees = db.query(Employee).all()
    results = []
    for emp in employees:
        try:
            # When evaluating all company employees, enable AI on-demand or when forced
            item = calculate_employee_burnout(emp.id, db, use_ai=force_ai)
            results.append(item)
        except Exception as e:
            logger.error(f"Error analyzing employee {emp.id}: {e}")
            continue

    # Sort descending by burnout score (highest risk first)
    results.sort(key=lambda x: x.burnout_score, reverse=True)
    return results

def calculate_company_burnout_summary(db: Session) -> BurnoutSummaryResponse:
    items = analyze_company_burnout(db, force_ai=False)
    total = len(items)
    if total == 0:
        return BurnoutSummaryResponse(
            total_evaluated=0,
            avg_burnout_score=0.0,
            company_work_life_balance=100.0,
            critical_count=0,
            high_count=0,
            medium_count=0,
            low_count=0,
            top_stressors=["No employee records available"],
            executive_summary="No employee health telemetry recorded."
        )

    avg_score = round(sum(i.burnout_score for i in items) / total, 1)
    avg_wlb = round(sum(i.work_life_balance_score for i in items) / total, 1)

    crit_cnt = sum(1 for i in items if i.risk_level == "CRITICAL")
    high_cnt = sum(1 for i in items if i.risk_level == "HIGH")
    med_cnt = sum(1 for i in items if i.risk_level == "MEDIUM")
    low_cnt = sum(1 for i in items if i.risk_level == "LOW")

    # Aggregate stressors
    stressor_counts: Dict[str, int] = {}
    for i in items:
        for s in i.key_stressors:
            stressor_counts[s] = stressor_counts.get(s, 0) + 1

    top_stressors = sorted(stressor_counts.keys(), key=lambda k: stressor_counts[k], reverse=True)[:5]
    if not top_stressors:
        top_stressors = ["Overtime work hours", "Task backlog pressure", "Vacation deficit"]

    executive_summary = (
        f"Company Well-being Audit evaluated {total} employees. Overall workplace burnout index is {avg_score}/100 "
        f"with a Work-Life Balance average of {avg_wlb}/100. There are {crit_cnt} employee(s) in Critical risk and "
        f"{high_cnt} in High risk categories needing proactive managerial intervention."
    )

    return BurnoutSummaryResponse(
        total_evaluated=total,
        avg_burnout_score=avg_score,
        company_work_life_balance=avg_wlb,
        critical_count=crit_cnt,
        high_count=high_cnt,
        medium_count=med_cnt,
        low_count=low_cnt,
        top_stressors=top_stressors,
        executive_summary=executive_summary
    )
