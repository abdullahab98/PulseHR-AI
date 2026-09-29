import json
import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models import (
    Employee, Department, Project, Task, Attendance, LeaveRequest,
    ProjectStatus, TaskStatus, TaskPriority, LeaveStatus, AttendanceStatus
)
from app.schemas import ReportGenerationResponse
from app.services.ai_engine import ai_engine
from app.services.burnout_analyzer import calculate_company_burnout_summary

logger = logging.getLogger(__name__)

def sanitize_report_markdown(text: str) -> str:
    if not text:
        return text
    # Clean LaTeX math notations such as $\ge 85.0\%$, \ge, \le, etc.
    text = re.sub(r'\$\\ge\s*([^$]*)\$', r'>= \1', text)
    text = re.sub(r'\\ge\b', '>=', text)
    text = re.sub(r'\$\\le\s*([^$]*)\$', r'<= \1', text)
    text = re.sub(r'\\le\b', '<=', text)
    text = re.sub(r'\$\\approx\s*([^$]*)\$', r'≈ \1', text)
    text = re.sub(r'\\approx\b', '≈', text)
    text = re.sub(r'\$\\times\s*([^$]*)\$', r'× \1', text)
    text = re.sub(r'\\times\b', '×', text)
    # Strip unnecessary math mode enclosing dollar signs like $<30.0/100$
    text = re.sub(r'\$([<>=!~+\-0-9.%/a-zA-Z\s]+)\$', r'\1', text)
    text = text.replace(r'\%', '%')
    return text

def generate_ai_report(
    report_type: str,
    start_date: date,
    end_date: date,
    db: Session,
    department_id: Optional[int] = None,
    focus_area: Optional[str] = None
) -> ReportGenerationResponse:
    report_type_upper = report_type.upper()
    
    # 1. SCOPE & EMPLOYEE TELEMETRY
    emp_query = db.query(Employee)
    if department_id:
        emp_query = emp_query.filter(Employee.department_id == department_id)
    employees = emp_query.all()
    total_employees = len(employees)
    employee_ids = [e.id for e in employees]

    dept_breakdown: Dict[str, int] = {}
    departments = db.query(Department).all()
    for d in departments:
        cnt = db.query(Employee).filter(Employee.department_id == d.id).count()
        dept_breakdown[d.name] = cnt

    target_dept_name = None
    if department_id:
        target_dept = db.query(Department).filter(Department.id == department_id).first()
        target_dept_name = target_dept.name if target_dept else None

    # 2. PROJECTS TELEMETRY
    proj_query = db.query(Project)
    if department_id:
        proj_query = proj_query.filter(Project.department_id == department_id)
    projects = proj_query.all()
    
    total_projects = len(projects)
    active_projects = sum(1 for p in projects if p.status == ProjectStatus.IN_PROGRESS)
    delayed_projects = sum(1 for p in projects if p.status == ProjectStatus.DELAYED)
    completed_projects = sum(1 for p in projects if p.status == ProjectStatus.COMPLETED)
    planning_projects = sum(1 for p in projects if p.status == ProjectStatus.PLANNING)
    on_hold_projects = sum(1 for p in projects if p.status == ProjectStatus.ON_HOLD)

    top_projects_data = []
    for p in projects[:6]:
        top_projects_data.append({
            "title": p.title,
            "status": str(p.status.value) if hasattr(p.status, 'value') else str(p.status),
            "start_date": str(p.start_date) if p.start_date else None,
            "end_date": str(p.end_date) if p.end_date else None,
            "budget": float(p.budget) if getattr(p, 'budget', None) else 0.0
        })

    # 3. TASKS TELEMETRY
    task_query = db.query(Task)
    if employee_ids:
        task_query = task_query.filter(Task.assignee_id.in_(employee_ids))
    tasks = task_query.all()

    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.DONE)
    in_progress_tasks = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
    todo_tasks = sum(1 for t in tasks if t.status == TaskStatus.TODO)
    
    today = date.today()
    overdue_tasks = sum(1 for t in tasks if t.status != TaskStatus.DONE and t.due_date and t.due_date < today)
    urgent_tasks = sum(1 for t in tasks if t.status != TaskStatus.DONE and t.priority in [TaskPriority.HIGH, TaskPriority.URGENT])
    task_completion_rate = round((completed_tasks / max(total_tasks, 1)) * 100, 1)

    # 4. ATTENDANCE & WORKLOAD TELEMETRY
    att_query = db.query(Attendance).filter(Attendance.date >= start_date, Attendance.date <= end_date)
    if employee_ids:
        att_query = att_query.filter(Attendance.employee_id.in_(employee_ids))
    attendance_records = att_query.all()

    total_att_logs = len(attendance_records)
    total_work_hours = sum(a.work_hours for a in attendance_records)
    total_overtime_hours = sum(a.overtime_hours for a in attendance_records)
    avg_daily_work_hours = round(total_work_hours / max(total_att_logs, 1), 1)
    late_arrivals_count = sum(1 for a in attendance_records if a.status == AttendanceStatus.LATE)
    weekend_shifts_count = sum(1 for a in attendance_records if a.date.weekday() >= 5)

    # 5. LEAVES & TIME-OFF DEFICIT
    leave_query = db.query(LeaveRequest).filter(
        LeaveRequest.created_at >= datetime.combine(start_date, datetime.min.time()),
        LeaveRequest.created_at <= datetime.combine(end_date, datetime.max.time())
    )
    if employee_ids:
        leave_query = leave_query.filter(LeaveRequest.employee_id.in_(employee_ids))
    leave_records = leave_query.all()

    total_leave_requests = len(leave_records)
    pending_leaves = sum(1 for l in leave_records if l.status == LeaveStatus.PENDING)
    approved_leaves = sum(1 for l in leave_records if l.status == LeaveStatus.APPROVED)

    # 6. BURNOUT & PSYCHOLOGICAL RADAR TELEMETRY
    avg_burnout_score = 0.0
    critical_burnout_count = 0
    high_burnout_count = 0
    try:
        b_summary = calculate_company_burnout_summary(db)
        avg_burnout_score = b_summary.avg_burnout_score
        critical_burnout_count = b_summary.critical_count
        high_burnout_count = b_summary.high_count
    except Exception as e:
        logger.warning(f"Could not calculate burnout summary: {e}")

    # 7. CONSOLIDATED METRICS OBJECT
    metrics = {
        "time_period": f"{start_date} to {end_date}",
        "scope": f"Department: {target_dept_name}" if target_dept_name else "All Enterprise Departments",
        "total_employees": total_employees,
        "department_distribution": dept_breakdown,
        "total_projects": total_projects,
        "active_projects": active_projects,
        "delayed_projects": delayed_projects,
        "completed_projects": completed_projects,
        "planning_projects": planning_projects,
        "on_hold_projects": on_hold_projects,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "in_progress_tasks": in_progress_tasks,
        "todo_tasks": todo_tasks,
        "overdue_tasks": overdue_tasks,
        "urgent_priority_tasks": urgent_tasks,
        "task_completion_rate": task_completion_rate,
        "attendance_logs_count": total_att_logs,
        "avg_daily_work_hours": avg_daily_work_hours,
        "total_overtime_hours": round(total_overtime_hours, 1),
        "late_arrivals_count": late_arrivals_count,
        "weekend_shifts_count": weekend_shifts_count,
        "pending_leave_requests": pending_leaves,
        "approved_leave_requests": approved_leaves,
        "avg_burnout_score": avg_burnout_score,
        "critical_burnout_alerts": critical_burnout_count,
        "high_burnout_alerts": high_burnout_count
    }

    # 8. INTELLIGENT REPORT PROMPT TO GEMINI
    report_title_map = {
        "DAILY": "Daily Operations & Activity Pulse Report",
        "WEEKLY": "Weekly Executive Operations & Productivity Briefing",
        "MONTHLY": "Monthly Enterprise Performance & Retrospective Dossier",
        "PROJECT_AUDIT": "Project Portfolio Velocity & Bottleneck Risk Audit",
        "HR_WELLNESS": "Workforce Biometrics, Well-being & Burnout Radar Report",
        "EXECUTIVE_BOARD": "C-Level Executive & Board Operations Briefing"
    }
    report_title = report_title_map.get(report_type_upper, f"Executive Operations Report ({report_type_upper})")
    if target_dept_name:
        report_title += f" - {target_dept_name}"

    ai_prompt = f"""
You are the Chief Operations Intelligence AI for an enterprise management system.
Generate an exhaustive, highly structured, C-level executive operations report in GitHub-flavored Markdown.

REPORT TYPE: {report_type_upper} ({report_title})
REPORTING TIMEFRAME: {start_date} to {end_date}
TARGET SCOPE: {metrics['scope']}
CUSTOM FOCUS INSTRUCTION: {focus_area or 'Comprehensive operational review covering delivery velocity, workforce productivity, and friction points.'}

CONSOLIDATED TELEMETRY DATA:
- Monitored Active Employees: {total_employees}
- Department Breakdown: {json.dumps(dept_breakdown)}
- Projects Status: {active_projects} Active, {delayed_projects} Delayed, {completed_projects} Completed, {planning_projects} Planning, {on_hold_projects} On Hold (Total: {total_projects})
- Key Projects Sample: {json.dumps(top_projects_data)}
- Task Velocity: {completed_tasks}/{total_tasks} completed ({task_completion_rate}% completion rate). In Progress: {in_progress_tasks}, Todo: {todo_tasks}
- Overdue Deadlines: {overdue_tasks} overdue tasks, {urgent_tasks} high/urgent priority tasks
- Attendance & Punctuality: {total_att_logs} check-in sessions, Avg Daily Work: {avg_daily_work_hours} hrs/day, Total Overtime: {metrics['total_overtime_hours']} hrs, Late Check-ins: {late_arrivals_count}, Weekend Shifts: {weekend_shifts_count}
- Rest & Leave Flow: {pending_leaves} pending applications, {approved_leaves} approved
- Well-being & Burnout Radar: Avg Burnout Index {avg_burnout_score}/100, Critical Alerts: {critical_burnout_count}, High Alerts: {high_burnout_count}

OUTPUT STRUCTURE REQUIREMENTS:
Please format your response into two distinct parts:
1. First, provide a valid JSON code block ```json ... ``` with this exact structure:
{{
  "executive_takeaways": [
    "Key takeaway 1 (one clear, data-backed sentence)",
    "Key takeaway 2",
    "Key takeaway 3"
  ],
  "strategic_recommendations": [
    "Actionable managerial recommendation 1",
    "Actionable managerial recommendation 2",
    "Actionable managerial recommendation 3"
  ],
  "risk_level": "LOW" | "MODERATE" | "HIGH" | "CRITICAL",
  "summary": "Crisp 2-sentence executive summary paragraph."
}}

2. Followed by the complete, comprehensive Markdown report formatted with professional styling:
# {report_title}
> **Reporting Period:** {start_date} to {end_date} | **Scope:** {metrics['scope']} | **Status:** Generated via AI Operations Engine

## 1. Executive Summary & Verdict
(Provide a rigorous analysis of overall health, productivity highlights, and primary risks)

## 2. Key Operational Metrics Matrix
(Format with a clean Markdown comparison table displaying target vs actuals)

## 3. Project Velocity & Delivery Milestones
(Breakdown active deliverables, project progress, delays, and task completion velocity)

## 4. Workforce Dynamics & Attendance Telemetry
(Punctuality, overtime distribution, weekend workloads, and rest deficits)

## 5. Well-being & Burnout Radar
(Psychological friction, risk areas, retention implications)

## 6. Strategic Roadblocks & Remediation Action Plan
(Step-by-step immediate next steps for management over the next 14 to 30 days)

Do not use phrases mentioning specific LLM model names. Speak with authoritative, corporate analytical tone.
CRITICAL FORMATTING INSTRUCTION: Do NOT use LaTeX math notation (NEVER use $\ge$, $\le$, $\approx$, or math dollar signs $). Always write standard comparison symbols like >=, <=, >, <, %, or text (e.g. '>= 85%', '<= 30%').
"""

    system_instruction = "You are an Enterprise Chief Operating Officer AI Assistant. You produce data-grounded, sophisticated executive operational reports in Markdown and structured JSON."
    
    markdown_content = ""
    executive_takeaways = []
    strategic_recommendations = []
    risk_level = "MODERATE"
    summary_text = ""

    try:
        raw_response = ai_engine.generate_text(ai_prompt, system_instruction=system_instruction)
        
        # Check if JSON block exists
        if "```json" in raw_response:
            parts = raw_response.split("```json")
            json_part = parts[1].split("```")[0].strip()
            markdown_part = parts[1].split("```", 1)[1].strip()
            
            try:
                parsed_json = json.loads(json_part)
                executive_takeaways = parsed_json.get("executive_takeaways", [])
                strategic_recommendations = parsed_json.get("strategic_recommendations", [])
                risk_level = parsed_json.get("risk_level", "MODERATE")
                summary_text = parsed_json.get("summary", "")
            except Exception as e:
                logger.warning(f"Error parsing JSON from report generation: {e}")
            
            markdown_content = markdown_part if markdown_part else raw_response
        else:
            markdown_content = raw_response
            summary_text = raw_response.split("\n\n")[0].replace("#", "").strip()

    except Exception as e:
        logger.error(f"AI Report generation error: {e}")
        # Deterministic rich fallback report
        risk_level = "CRITICAL" if critical_burnout_count > 0 or delayed_projects > 0 else "MODERATE"
        summary_text = f"Operations evaluation for period {start_date} to {end_date}. Monitored {total_employees} personnel across {total_projects} projects with {task_completion_rate}% task completion rate."
        executive_takeaways = [
            f"Active deliverables running at {task_completion_rate}% task completion with {overdue_tasks} overdue tasks.",
            f"Overtime accumulation reached {metrics['total_overtime_hours']} hours with {late_arrivals_count} late check-in instances.",
            f"Workforce health radar detected {critical_burnout_count} critical and {high_burnout_count} high burnout risk personnel."
        ]
        strategic_recommendations = [
            "Reallocate urgent task bottlenecks to under-utilized departments.",
            "Enforce mandatory rest and approve overdue leave applications to curb attrition risk.",
            "Schedule project re-alignment for delayed initiatives."
        ]
        markdown_content = f"""# {report_title}
> **Reporting Period:** {start_date} to {end_date} | **Scope:** {metrics['scope']}

## 1. Executive Summary & Verdict
During the specified operational cycle, the organization monitored **{total_employees} active team members** handling **{total_projects} projects** and **{total_tasks} individual tasks**. 

Overall operational velocity registered a **{task_completion_rate}% task completion rate**. Punctuality records indicate **{late_arrivals_count} late arrivals** alongside **{metrics['total_overtime_hours']} hours of accumulated overtime**.

## 2. Key Operational Metrics Matrix
| Metric Category | Current Telemetry | Operational Assessment |
| :--- | :--- | :--- |
| **Total Monitored Personnel** | {total_employees} Employees | Enterprise Capacity Baseline |
| **Active Projects** | {active_projects} In-Progress | Delivery Pipeline Active |
| **Delayed Projects** | {delayed_projects} Delayed | Requires Immediate Alignment |
| **Task Completion Rate** | {task_completion_rate}% ({completed_tasks}/{total_tasks}) | Execution Efficiency |
| **Overdue Tasks** | {overdue_tasks} Tasks | Delivery Risk Factor |
| **Average Daily Work Hours** | {avg_daily_work_hours} hrs/day | Workload Index |
| **Total Overtime Hours** | {metrics['total_overtime_hours']} hrs | Fatigue Indicator |
| **High/Critical Burnout Risk** | {critical_burnout_count + high_burnout_count} Employees | Retention Priority |

## 3. Project Velocity & Delivery Milestones
- **Active Projects:** {active_projects} ongoing workstreams.
- **Delayed Milestones:** {delayed_projects} projects have encountered schedule slippage.
- **Task Bottlenecks:** {urgent_tasks} high or urgent priority tasks currently require immediate completion.

## 4. Workforce Dynamics & Rest Flow
- Total Attendance Records: **{total_att_logs} sessions**
- Overtime Logged: **{metrics['total_overtime_hours']} hours**
- Pending Leave Requests: **{pending_leaves} requests** awaiting management decision.

## 5. Strategic Next Steps
1. Immediate milestone triage for all delayed projects.
2. Balance workload across departments to alleviate overtime burnout.
3. Process pending leave applications to provide required rest cycles.
"""

    if not summary_text:
        summary_text = f"Executive operations report for {metrics['scope']} ({start_date} to {end_date})."

    if not executive_takeaways:
        executive_takeaways = [
            f"Overall task completion velocity is at {task_completion_rate}%.",
            f"Tracked {active_projects} active and {delayed_projects} delayed projects.",
            f"Total overtime recorded: {metrics['total_overtime_hours']} hrs across {total_att_logs} shifts."
        ]

    if not strategic_recommendations:
        strategic_recommendations = [
            "Optimize task distribution to resolve overdue bottlenecks.",
            "Review workload distribution in departments reporting elevated overtime.",
            "Realign milestone schedules for delayed deliverables."
        ]

    markdown_content = sanitize_report_markdown(markdown_content)
    summary_text = sanitize_report_markdown(summary_text)

    return ReportGenerationResponse(
        report_type=report_type_upper,
        generated_at=datetime.utcnow(),
        title=report_title,
        summary=summary_text[:300],
        metrics=metrics,
        markdown_content=markdown_content,
        executive_takeaways=executive_takeaways,
        strategic_recommendations=strategic_recommendations,
        risk_level=risk_level
    )
