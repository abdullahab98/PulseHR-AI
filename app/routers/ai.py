from typing import List, Optional
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    User, Employee, Project, ProjectStatus, Task, TaskStatus, 
    Attendance, AttendanceStatus, LeaveRequest, LeaveStatus
)
from app.schemas import (
    AIAssistantQuery, AIAssistantResponse,
    TaskRecommendationRequest, TaskRecommendationResponse,
    BurnoutAnalysisItem, BurnoutSummaryResponse,
    ReportGenerationRequest, ReportGenerationResponse
)
from app.security import get_current_user
from app.services.ai_engine import ai_engine
from app.services.burnout_analyzer import analyze_company_burnout, calculate_employee_burnout, calculate_company_burnout_summary
from app.services.task_recommender import evaluate_task_assignments
from app.services.report_generator import generate_ai_report

router = APIRouter(prefix="/ai", tags=["AI Features Engine"])

import time

_METRICS_CACHE = {
    "timestamp": 0,
    "data": None
}

def _get_cached_enterprise_metrics(db: Session, today: date):
    now = time.time()
    if _METRICS_CACHE["data"] and (now - _METRICS_CACHE["timestamp"] < 30):
        return _METRICS_CACHE["data"]

    total_employees = db.query(Employee).count()
    all_projects = db.query(Project).all()
    delayed_projects = [p for p in all_projects if p.status == ProjectStatus.DELAYED]
    active_projects = [p for p in all_projects if p.status == ProjectStatus.IN_PROGRESS]
    delayed_names = ", ".join([p.title for p in delayed_projects]) if delayed_projects else "None"
    
    total_tasks = db.query(Task).count()
    done_tasks = db.query(Task).filter(Task.status == TaskStatus.DONE).count()
    completion_rate = round((done_tasks / max(total_tasks, 1)) * 100, 1)

    today_att = db.query(Attendance).filter(Attendance.date == today).all()
    present_count = sum(1 for a in today_att if a.status in [AttendanceStatus.PRESENT, AttendanceStatus.LATE])
    late_count = sum(1 for a in today_att if a.status == AttendanceStatus.LATE)
    att_rate = round((present_count / max(total_employees, 1)) * 100, 1)

    burnout_items = analyze_company_burnout(db)
    overloaded_employees = [item for item in burnout_items if item.risk_level in ["HIGH", "CRITICAL"]]
    overloaded_summary = ", ".join([f"{item.employee_name} ({item.risk_level} Risk, Score {item.burnout_score})" for item in overloaded_employees]) if overloaded_employees else "None (balanced workload)"
    pending_leaves = db.query(LeaveRequest).filter(LeaveRequest.status == LeaveStatus.PENDING).count()

    data = {
        "total_employees": total_employees,
        "all_projects": all_projects,
        "delayed_projects": delayed_projects,
        "active_projects": active_projects,
        "delayed_names": delayed_names,
        "total_tasks": total_tasks,
        "done_tasks": done_tasks,
        "completion_rate": completion_rate,
        "present_count": present_count,
        "late_count": late_count,
        "att_rate": att_rate,
        "overloaded_employees": overloaded_employees,
        "overloaded_summary": overloaded_summary,
        "pending_leaves": pending_leaves
    }
    _METRICS_CACHE["timestamp"] = now
    _METRICS_CACHE["data"] = data
    return data

@router.post("/assistant", response_model=AIAssistantResponse)
def executive_assistant_query(
    query_in: AIAssistantQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q_lower = query_in.query.lower().strip()
    today = date.today()

    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    user_name = f"{emp.first_name} {emp.last_name}" if emp else (current_user.email or "Executive")
    user_role = str(current_user.role.value if hasattr(current_user.role, 'value') else current_user.role)

    # 1. Instant Fast-Path: Standard Greetings (< 5ms response time)
    if q_lower in ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening"]:
        return AIAssistantResponse(
            answer=(
                f"Hello **{user_name}**! I am **PulseHR AI**, your enterprise smart assistant.\n\n"
                f"I am ready to assist you with company operations, projects, tasks, attendance, employee workloads, "
                f"as well as general questions, coding, email drafting, and strategic advice. How can I help you right now?"
            )
        )

    # 2. Instant Fast-Path: Capabilities / Help (< 5ms response time)
    if any(q_lower == p or q_lower.startswith(p) for p in ["what can you do", "who are you", "what are your capabilities", "help", "how can you help"]):
        return AIAssistantResponse(
            answer=(
                f"I am **PulseHR AI**, powered by Google Gemini.\n\n"
                f"**Here is what I can do:**\n"
                f"• **Live Office Operations:** Check real-time project health, attendance rates, task completion, and employee burnout risks.\n"
                f"• **Drafting & Writing:** Compose professional emails, meeting agendas, leave requests, and executive summaries.\n"
                f"• **Code & Technical Assistance:** Write, debug, and explain code in Python, TypeScript, Angular, SQL, and APIs.\n"
                f"• **General Intelligence:** Answer questions across business, technology, productivity, and everyday tasks.\n\n"
                f"Feel free to ask any question or click a quick action above!"
            )
        )

    # 3. Retrieve live enterprise metrics (cached for 30s for maximum speed)
    metrics = _get_cached_enterprise_metrics(db, today)
    total_employees = metrics["total_employees"]
    all_projects = metrics["all_projects"]
    delayed_projects = metrics["delayed_projects"]
    active_projects = metrics["active_projects"]
    delayed_names = metrics["delayed_names"]
    total_tasks = metrics["total_tasks"]
    done_tasks = metrics["done_tasks"]
    completion_rate = metrics["completion_rate"]
    present_count = metrics["present_count"]
    late_count = metrics["late_count"]
    att_rate = metrics["att_rate"]
    overloaded_employees = metrics["overloaded_employees"]
    overloaded_summary = metrics["overloaded_summary"]
    pending_leaves = metrics["pending_leaves"]

    # 4. Instant Fast-Path: Direct Office Queries (< 10ms response time)
    if any(k in q_lower for k in ["delayed project", "show delayed", "overdue project"]):
        if delayed_projects:
            msg = f"Found **{len(delayed_projects)} delayed project(s)**:\n" + "\n".join([f"• **{p.title}** (Budget: ${p.budget:,.2f})" for p in delayed_projects]) + "\n\n*Recommendation:* Review milestone blockers and reallocate sprint resources."
        else:
            msg = "✅ **All Projects On Track**: There are currently no delayed projects across the organization."
        return AIAssistantResponse(
            answer=msg,
            action_type="NAVIGATE_PROJECTS",
            data={"projects": [{"id": p.id, "title": p.title, "budget": p.budget, "status": p.status.value if hasattr(p.status, 'value') else str(p.status)} for p in delayed_projects], "total_delayed": len(delayed_projects)}
        )

    if any(k in q_lower for k in ["attendance summary", "today's attendance", "attendance rate"]):
        msg = f"📊 **Today's Attendance Overview**:\n• **Checked In:** {present_count} / {total_employees} employees ({att_rate}% rate)\n• **Late Arrivals:** {late_count}\n• **Pending Check-ins:** {max(total_employees - present_count, 0)}"
        return AIAssistantResponse(
            answer=msg,
            action_type="SHOW_ATTENDANCE",
            data={"present": present_count, "total": total_employees, "late": late_count, "rate": att_rate}
        )

    if any(k in q_lower for k in ["who is overloaded", "employee overload", "burnout summary", "burnout risk"]):
        if overloaded_employees:
            msg = f"⚠️ **Employee Overload & Burnout Alert**:\nThe following **{len(overloaded_employees)} employee(s)** are currently at high risk of burnout:\n" + "\n".join([f"• **{item.employee_name}** — Risk: `{item.risk_level}`, Score: `{item.burnout_score}/100`" for item in overloaded_employees]) + "\n\n*Action:* Consider redistributing sprint tickets and scheduling wellness check-ins."
        else:
            msg = "✅ **Workload Balanced**: All active employees currently maintain healthy workload metrics."
        return AIAssistantResponse(
            answer=msg,
            action_type="NAVIGATE_BURNOUT",
            data={"overloaded": [item.dict() for item in overloaded_employees], "count": len(overloaded_employees)}
        )

    if any(k in q_lower for k in ["office summary", "company summary", "executive summary", "status summary"]):
        msg = (
            f"🏢 **Executive Operational Summary for {user_name}**:\n"
            f"• **Workforce:** {total_employees} total employees\n"
            f"• **Attendance:** {present_count}/{total_employees} present today ({att_rate}%, {late_count} late)\n"
            f"• **Projects:** {len(active_projects)} active, {len(delayed_projects)} delayed\n"
            f"• **Tasks:** {done_tasks}/{total_tasks} completed ({completion_rate}% completion rate)\n"
            f"• **Burnout Alerts:** {len(overloaded_employees)} employees at risk\n"
            f"• **Pending Leaves:** {pending_leaves} awaiting approval"
        )
        return AIAssistantResponse(
            answer=msg,
            action_type="SHOW_PRODUCTIVITY",
            data={"completion_rate": completion_rate, "done_tasks": done_tasks, "total_tasks": total_tasks}
        )

    if any(k in q_lower for k in ["team productivity", "task completion rate", "productivity"]):
        msg = f"🚀 **Team Productivity Index**:\n• **Task Completion Rate:** {completion_rate}%\n• **Completed Tasks:** {done_tasks} of {total_tasks}\n• **Pending Deliverables:** {total_tasks - done_tasks}"
        return AIAssistantResponse(
            answer=msg,
            action_type="SHOW_PRODUCTIVITY",
            data={"completion_rate": completion_rate, "done_tasks": done_tasks, "total_tasks": total_tasks}
        )

    # 5. For generative, complex, or open-ended inquiries: Call Gemini with streamlined prompt
    history_context = ""
    if query_in.history:
        formatted_history = []
        for msg in query_in.history[-4:]:
            sender = "User" if msg.get("sender") == "user" else "Assistant"
            text_content = msg.get("text", "").strip()
            if text_content:
                formatted_history.append(f"{sender}: {text_content}")
        if formatted_history:
            history_context = "Recent Conversation:\n" + "\n".join(formatted_history) + "\n\n"

    system_instruction = (
        "You are PulseHR AI, an intelligent, articulate, and rapid AI Assistant integrated into an enterprise office management system, powered by Gemini.\n"
        "GUIDELINES:\n"
        "1. Be direct, clear, professional, and concise. Avoid unnecessary conversational filler.\n"
        "2. Answer ANY question asked — coding, writing, emails, math, science, business, or casual inquiries.\n"
        "3. When asked about company data, use the provided live operational metrics.\n"
        "4. Always identify yourself as PulseHR AI when asked your name or who you are.\n"
        "5. Always respond in fluent, polished English."
    )

    prompt = (
        f"{history_context}"
        f"Office Context: User {user_name} ({user_role}), {total_employees} staff, "
        f"{len(active_projects)} active projects, {len(delayed_projects)} delayed, "
        f"{done_tasks}/{total_tasks} tasks done ({completion_rate}%), "
        f"{present_count}/{total_employees} present today, {pending_leaves} pending leaves.\n\n"
        f"User Query: '{query_in.query}'\n\n"
        f"Provide a direct, high-value, and helpful answer in English."
    )

    ai_answer = ai_engine.generate_text(prompt, system_instruction=system_instruction, max_tokens=650)

    if not ai_answer or ai_answer.startswith("[AI Analysis Summary]"):
        ai_answer = (
            f"I have received your inquiry: **\"{query_in.query}\"**.\n\n"
            f"Current office telemetry shows {present_count}/{total_employees} staff present ({att_rate}%) "
            f"and {len(active_projects)} active project(s). Please feel free to re-ask or specify details!"
        )

    return AIAssistantResponse(answer=ai_answer)


@router.get("/burnout/summary", response_model=BurnoutSummaryResponse)
def get_burnout_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return calculate_company_burnout_summary(db)


@router.get("/burnout", response_model=List[BurnoutAnalysisItem])
def get_burnout_analytics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return analyze_company_burnout(db)


@router.get("/burnout/{employee_id}", response_model=BurnoutAnalysisItem)
def get_single_burnout(employee_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return calculate_employee_burnout(employee_id, db, use_ai=False)
    except ValueError:
        raise HTTPException(status_code=404, detail="Employee not found")


@router.post("/burnout/generate-report/{employee_id}", response_model=BurnoutAnalysisItem)
def generate_employee_burnout_report(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        return calculate_employee_burnout(employee_id, db, use_ai=True)
    except ValueError:
        raise HTTPException(status_code=404, detail="Employee not found")


@router.post("/recommend-task", response_model=TaskRecommendationResponse)
def recommend_task_assignees(
    req: TaskRecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return evaluate_task_assignments(
        required_skills=req.required_skills,
        priority=req.priority,
        db=db,
        task_id=req.task_id
    )


@router.post("/generate-report", response_model=ReportGenerationResponse)
def generate_report(
    req: ReportGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    start_d = req.start_date or (date.today() - timedelta(days=30))
    end_d = req.end_date or date.today()
    return generate_ai_report(
        report_type=req.report_type,
        start_date=start_d,
        end_date=end_d,
        db=db,
        department_id=req.department_id,
        focus_area=req.focus_area
    )


@router.get("/dashboard-insights")
def get_dashboard_insights(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    scope = current_user.data_scope or ("ALL" if current_user.role == UserRole.SUPER_ADMIN else "DEPARTMENT" if current_user.role in [UserRole.DEPARTMENT_HEAD, UserRole.MANAGER] else "OWN")
    
    proj_query = db.query(Project)
    task_query = db.query(Task)

    if scope == "DEPARTMENT" and emp and emp.department_id:
        proj_query = proj_query.filter(Project.department_id == emp.department_id)
    elif scope == "OWN" and emp:
        task_query = task_query.filter(Task.assignee_id == emp.id)
        proj_query = proj_query.filter((Project.project_manager_id == emp.id) | (Project.department_id == emp.department_id))

    total_projects = proj_query.count()
    active_projects = proj_query.filter(Project.status == ProjectStatus.IN_PROGRESS).count()
    delayed_projects = proj_query.filter(Project.status == ProjectStatus.DELAYED).count()
    completed_projects = proj_query.filter(Project.status == ProjectStatus.COMPLETED).count()

    total_tasks = task_query.count()
    done_tasks = task_query.filter(Task.status == TaskStatus.DONE).count()

    burnout_items = analyze_company_burnout(db)
    if scope == "OWN" and emp:
        user_burnout = [b for b in burnout_items if b.employee_id == emp.id]
        burnout_items = user_burnout if user_burnout else burnout_items

    high_risk_count = sum(1 for b in burnout_items if b.risk_level in ["HIGH", "CRITICAL"])
    avg_burnout = round(sum(b.burnout_score for b in burnout_items) / max(len(burnout_items), 1), 1)

    project_health_score = round(max(0, 100 - (delayed_projects * 20)), 1)

    # Dynamic AI insights narrative tailored to user profile
    user_name = f"{emp.first_name} {emp.last_name}" if emp else current_user.email
    insights_prompt = (
        f"Summarize operational insights for {user_name} ({current_user.role.value}):\n"
        f"- Project Health Index: {project_health_score}%\n"
        f"- Active Projects: {active_projects}, Delayed: {delayed_projects}, Completed: {completed_projects}\n"
        f"- Task Velocity: {done_tasks}/{total_tasks} finished\n"
        f"- Average Employee Burnout Score: {avg_burnout}/100 ({high_risk_count} at risk)\n\n"
        f"Provide 3 actionable bullet points tailored for this user role."
    )
    
    ai_bullets = ai_engine.generate_text(insights_prompt, system_instruction="Provide role-tailored dashboard insights.")

    return {
        "user_email": current_user.email,
        "username": current_user.email,
        "user_role": current_user.role.value,
        "data_scope": scope,
        "project_health_score": project_health_score,
        "active_projects": active_projects,
        "delayed_projects": delayed_projects,
        "completed_projects": completed_projects,
        "total_tasks": total_tasks,
        "task_completion_rate": round((done_tasks / max(total_tasks, 1)) * 100, 1),
        "average_burnout_score": avg_burnout,
        "high_risk_employees": high_risk_count,
        "ai_insights_narrative": ai_bullets
    }
