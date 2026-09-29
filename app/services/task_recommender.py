from typing import List
from sqlalchemy.orm import Session
from app.models import Employee, Task, TaskStatus
from app.schemas import TaskRecommendationItem, TaskRecommendationResponse, TaskPriority

def evaluate_task_assignments(
    required_skills: List[str],
    priority: TaskPriority,
    db: Session,
    task_id: int = None
) -> TaskRecommendationResponse:
    employees = db.query(Employee).all()
    recommendations = []

    req_skills_set = set(s.lower().strip() for s in required_skills)

    for emp in employees:
        emp_skills_set = set(s.lower().strip() for s in emp.skills or [])
        
        # 1. Skill Match Calculation (Jaccard / Overlap Ratio)
        if req_skills_set:
            matched_skills = req_skills_set.intersection(emp_skills_set)
            skill_ratio = len(matched_skills) / len(req_skills_set)
        else:
            skill_ratio = 0.5  # Neutral if no required skills specified
        
        skill_match_pct = round(skill_ratio * 100, 1)

        # 2. Workload Capacity Calculation
        active_tasks = db.query(Task).filter(
            Task.assignee_id == emp.id,
            Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW])
        ).all()
        active_count = len(active_tasks)

        if active_count <= 2:
            workload_level = "Low"
            workload_factor = 1.0
        elif active_count <= 4:
            workload_level = "Moderate"
            workload_factor = 0.75
        elif active_count <= 6:
            workload_level = "High"
            workload_factor = 0.40
        else:
            workload_level = "Overloaded"
            workload_factor = 0.10

        # Priority weight adjustments
        prio_weight = 1.2 if priority in [TaskPriority.HIGH, TaskPriority.URGENT] else 1.0

        # Composite match score: 60% Skill Match + 40% Workload Availability
        raw_match = (skill_ratio * 60.0 + workload_factor * 40.0)
        match_score = round(min(max(raw_match, 10.0), 99.5), 1)

        # Confidence Score calculation
        confidence = round(min(match_score * 0.9 + (10 if skill_ratio > 0.7 else 0), 98.0), 1)

        # Natural language rationale
        matched_list = list(req_skills_set.intersection(emp_skills_set))
        if matched_list:
            skills_str = ", ".join(matched_list).title()
            reasoning = f"Direct skill overlap on {skills_str}. Workload is {workload_level} ({active_count} active tasks)."
        else:
            reasoning = f"Broad experience profile. Current workload is {workload_level} with {active_count} tasks."

        recommendations.append(
            TaskRecommendationItem(
                employee_id=emp.id,
                employee_name=f"{emp.first_name} {emp.last_name}",
                designation=emp.designation,
                match_score=match_score,
                confidence_score=confidence,
                reasoning=reasoning,
                skill_match_percentage=skill_match_pct,
                current_workload_level=workload_level
            )
        )

    # Sort recommendations by highest match score
    recommendations.sort(key=lambda x: x.match_score, reverse=True)

    return TaskRecommendationResponse(recommendations=recommendations[:5])
