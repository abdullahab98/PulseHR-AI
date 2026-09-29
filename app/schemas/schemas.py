from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any, Dict
from datetime import datetime, date, time
from app.models import UserRole, AttendanceStatus, LeaveType, LeaveStatus, ProjectStatus, TaskPriority, TaskStatus, BugStatus, TicketStatus

# --- Auth & User Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    email: str
    role: UserRole
    employee_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    allowed_panels: List[str] = []
    custom_permissions: Dict[str, Any] = {}
    panel_permissions: Optional[Dict[str, Any]] = None
    designation_name: Optional[str] = None
    data_scope: str = "OWN"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: UserRole = UserRole.EMPLOYEE
    employee_code: str
    department_id: Optional[int] = None
    designation: str = "Software Engineer"
    salary: float = 0.0

class UserResponse(BaseModel):
    id: int
    email: str
    role: UserRole
    is_active: bool
    allowed_panels: List[str] = []
    custom_permissions: Dict[str, Any] = {}
    data_scope: str = "OWN"
    created_at: datetime

    class Config:
        from_attributes = True

class UserPermissionUpdate(BaseModel):
    user_id: int
    role: Optional[UserRole] = None
    allowed_panels: Optional[List[str]] = None
    custom_permissions: Optional[Dict[str, Any]] = None
    data_scope: Optional[str] = None


# --- Department Schemas ---
class DepartmentCreate(BaseModel):
    name: str
    code: str
    budget: float = 0.0

class DepartmentResponse(BaseModel):
    id: int
    name: str
    code: str
    budget: float
    created_at: datetime

    class Config:
        from_attributes = True


# --- Office Schemas ---
class OfficeCreate(BaseModel):
    name: str
    establishment: Optional[str] = None
    description: Optional[str] = None
    mission: Optional[str] = None
    vision: Optional[str] = None

class OfficeUpdate(BaseModel):
    name: Optional[str] = None
    establishment: Optional[str] = None
    description: Optional[str] = None
    mission: Optional[str] = None
    vision: Optional[str] = None

class OfficeResponse(BaseModel):
    id: int
    name: str
    establishment: Optional[str] = None
    description: Optional[str] = None
    mission: Optional[str] = None
    vision: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Rank Schemas ---
class RankCreate(BaseModel):
    name: str

class RankUpdate(BaseModel):
    name: Optional[str] = None

class RankResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Designation Schemas ---
class DesignationCreate(BaseModel):
    name: str
    office_id: Optional[int] = None
    rank_id: Optional[int] = None
    description: Optional[str] = None
    permissions: Dict[str, Any] = {}

class DesignationUpdate(BaseModel):
    name: Optional[str] = None
    office_id: Optional[int] = None
    rank_id: Optional[int] = None
    description: Optional[str] = None
    permissions: Optional[Dict[str, Any]] = None

class DesignationResponse(BaseModel):
    id: int
    name: str
    office_id: Optional[int] = None
    office_name: Optional[str] = None
    rank_id: Optional[int] = None
    rank_name: Optional[str] = None
    description: Optional[str] = None
    permissions: Dict[str, Any] = {}
    created_at: datetime
    employees_count: Optional[int] = 0

    class Config:
        from_attributes = True


# --- Employee Schemas ---
class EmergencyContact(BaseModel):
    name: str
    relation: str
    phone: str

class EmployeeDocument(BaseModel):
    name: str
    url: str

class EmployeeCreate(BaseModel):
    user_id: Optional[int] = None
    employee_code: str
    first_name: str
    last_name: str
    department_id: Optional[int] = None
    office_id: Optional[int] = None
    rank_id: Optional[int] = None
    designation_id: Optional[int] = None
    designation: Optional[str] = "Employee"
    salary: float = 0.0
    phone: Optional[str] = None
    personal_email: Optional[str] = None
    address_info: Optional[Dict[str, Any]] = None
    family_info: Optional[Dict[str, Any]] = None
    bio: Optional[str] = None
    skills: List[str] = []
    emergency_contact: Dict[str, str] = {}
    documents: List[Dict[str, str]] = []
    hire_date: Optional[date] = None

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    department_id: Optional[int] = None
    office_id: Optional[int] = None
    rank_id: Optional[int] = None
    designation_id: Optional[int] = None
    designation: Optional[str] = None
    salary: Optional[float] = None
    phone: Optional[str] = None
    personal_email: Optional[str] = None
    address_info: Optional[Dict[str, Any]] = None
    family_info: Optional[Dict[str, Any]] = None
    bio: Optional[str] = None
    skills: Optional[List[str]] = None
    emergency_contact: Optional[Dict[str, str]] = None

class EmployeeResponse(BaseModel):
    id: int
    user_id: int
    employee_code: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    role: Optional[UserRole] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    office_id: Optional[int] = None
    office_name: Optional[str] = None
    rank_id: Optional[int] = None
    rank_name: Optional[str] = None
    designation_id: Optional[int] = None
    designation_name: Optional[str] = None
    designation: str
    salary: float
    phone: Optional[str] = None
    personal_email: Optional[str] = None
    address_info: Optional[Dict[str, Any]] = None
    family_info: Optional[Dict[str, Any]] = None
    bio: Optional[str] = None
    skills: List[str] = []
    emergency_contact: Dict[str, str] = {}
    documents: List[Dict[str, str]] = []
    hire_date: date

    class Config:
        from_attributes = True

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# --- Attendance Schemas ---
class CheckInRequest(BaseModel):
    employee_id: Optional[int] = None

class CheckOutRequest(BaseModel):
    employee_id: Optional[int] = None

class AttendanceResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    work_hours: float
    overtime_hours: float
    status: AttendanceStatus

    class Config:
        from_attributes = True


# --- Time Slot Schemas ---
class TimeSlotCreate(BaseModel):
    name: str
    start_time: str
    end_time: str
    late_grace_minutes: int = 15
    is_active: bool = True
    description: Optional[str] = None

class TimeSlotResponse(BaseModel):
    id: int
    name: str
    start_time: str
    end_time: str
    late_grace_minutes: int
    is_active: bool
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Attendance Application Schemas ---
class AttendanceApplicationCreate(BaseModel):
    employee_id: Optional[int] = None
    date: date
    requested_check_in: Optional[str] = None
    requested_check_out: Optional[str] = None
    application_type: str = "Correction"
    reason: str

class AttendanceApplicationStatusUpdate(BaseModel):
    status: str

class AttendanceApplicationResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    date: date
    requested_check_in: Optional[str] = None
    requested_check_out: Optional[str] = None
    application_type: str
    reason: str
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Time Slot Application Schemas ---
class TimeSlotApplicationCreate(BaseModel):
    employee_id: Optional[int] = None
    time_slot_id: int
    effective_from: date
    reason: str

class TimeSlotApplicationStatusUpdate(BaseModel):
    status: str

class TimeSlotApplicationResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    time_slot_id: int
    time_slot_name: Optional[str] = None
    effective_from: date
    reason: str
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Weekend Setup Schemas ---
class WeekendSetupCreate(BaseModel):
    days: List[str]
    department_id: Optional[int] = None
    note: Optional[str] = None

class WeekendSetupResponse(BaseModel):
    id: int
    days: List[str]
    department_id: Optional[int] = None
    note: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Attendance Report Schemas ---
class AttendanceReportItem(BaseModel):
    id: int
    date: date
    employee_id: int
    employee_name: str
    department_name: Optional[str] = None
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    work_hours: float
    overtime_hours: float
    status: AttendanceStatus

class AttendanceReportSummary(BaseModel):
    total_records: int
    total_present: int
    total_late: int
    total_absent: int
    total_overtime_hours: float
    avg_work_hours: float

class AttendanceReportResponse(BaseModel):
    summary: AttendanceReportSummary
    records: List[AttendanceReportItem]



# --- Leave Schemas ---
class LeaveTypeConfigCreate(BaseModel):
    name: str
    code: str
    days_allowed: int = 15
    is_paid: bool = True
    requires_attachment: bool = False
    carry_forward: bool = False
    is_active: bool = True
    description: Optional[str] = None

class LeaveTypeConfigUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    days_allowed: Optional[int] = None
    is_paid: Optional[bool] = None
    requires_attachment: Optional[bool] = None
    carry_forward: Optional[bool] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None

class LeaveTypeConfigResponse(BaseModel):
    id: int
    name: str
    code: str
    days_allowed: int
    is_paid: bool
    requires_attachment: bool
    carry_forward: bool
    is_active: bool
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DesignationChainCreate(BaseModel):
    designation_id: int
    approver_designation_id: int
    level: int = 1
    auto_approve_days: int = 3
    notes: Optional[str] = None

class DesignationChainResponse(BaseModel):
    id: int
    designation_id: int
    designation_name: Optional[str] = None
    approver_designation_id: int
    approver_designation_name: Optional[str] = None
    level: int
    auto_approve_days: int
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeaveCreate(BaseModel):
    employee_id: int
    leave_type: str
    start_date: date
    end_date: date
    reason: str

class LeaveStatusUpdate(BaseModel):
    status: LeaveStatus

class LeaveResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    leave_type: str
    start_date: date
    end_date: date
    days_count: Optional[int] = 1
    reason: str
    status: LeaveStatus
    approved_by_id: Optional[int] = None
    approver_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- My Leave Report Schemas ---
class MyLeaveQuotaItem(BaseModel):
    leave_type: str
    name: str
    allocated: int
    used: int
    pending: int
    remaining: int
    is_paid: bool

class MyLeaveReportResponse(BaseModel):
    employee_id: int
    employee_name: str
    department_name: Optional[str] = None
    total_allocated: int
    total_used: int
    total_remaining: int
    total_pending: int
    quotas: List[MyLeaveQuotaItem]
    history: List[LeaveResponse]


# --- Employee Leave Report Schemas ---
class EmployeeLeaveReportItem(BaseModel):
    employee_id: int
    employee_name: str
    employee_code: Optional[str] = None
    department_name: Optional[str] = None
    designation_name: Optional[str] = None
    annual_allocated: int
    annual_used: int
    casual_used: int
    sick_used: int
    other_used: int
    total_used: int
    remaining_balance: int
    pending_applications: int

class EmployeeLeaveReportSummary(BaseModel):
    total_employees: int
    total_days_taken: int
    avg_leave_per_emp: float
    total_pending_requests: int
    most_used_leave_type: str

class EmployeeLeaveReportResponse(BaseModel):
    summary: EmployeeLeaveReportSummary
    department_breakdown: Dict[str, int]
    employees: List[EmployeeLeaveReportItem]


# --- Project Schemas ---
class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None
    department_id: int
    project_manager_id: Optional[int] = None
    budget: float = 0.0
    status: ProjectStatus = ProjectStatus.PLANNING
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    department_id: Optional[int] = None
    project_manager_id: Optional[int] = None
    budget: Optional[float] = None
    status: Optional[ProjectStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class ProjectResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    department_id: int
    department_name: Optional[str] = None
    project_manager_id: Optional[int] = None
    project_manager_name: Optional[str] = None
    budget: float
    status: ProjectStatus
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    task_count: Optional[int] = 0
    completed_task_count: Optional[int] = 0
    created_at: datetime

    class Config:
        from_attributes = True


# --- Task Schemas ---
class TaskCreate(BaseModel):
    project_id: int
    title: str
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[date] = None
    required_skills: List[str] = []
    progress: int = 0
    status: TaskStatus = TaskStatus.TODO
    dependencies: List[int] = []

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[date] = None
    required_skills: Optional[List[str]] = None
    progress: Optional[int] = None
    status: Optional[TaskStatus] = None
    dependencies: Optional[List[int]] = None

class TaskCommentCreate(BaseModel):
    comment: str

class TaskCommentResponse(BaseModel):
    id: int
    task_id: int
    author_id: int
    author_name: Optional[str] = None
    comment: str
    created_at: datetime

    class Config:
        from_attributes = True

class TaskResponse(BaseModel):
    id: int
    project_id: int
    project_title: Optional[str] = None
    title: str
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    assignee_name: Optional[str] = None
    priority: TaskPriority
    due_date: Optional[date] = None
    required_skills: List[str] = []
    progress: int
    status: TaskStatus
    dependencies: List[int] = []
    comments: List[TaskCommentResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


# --- Meeting Schemas ---
class MeetingCreate(BaseModel):
    title: str
    organizer_id: int
    scheduled_time: datetime
    duration_mins: int = 30
    attendees: List[int] = []
    raw_notes: Optional[str] = None

class MeetingSummaryRequest(BaseModel):
    raw_notes: str

class MeetingResponse(BaseModel):
    id: int
    title: str
    organizer_id: int
    organizer_name: Optional[str] = None
    scheduled_time: datetime
    duration_mins: int
    attendees: List[int] = []
    raw_notes: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_action_items: List[Dict[str, Any]] = []
    created_at: datetime

    class Config:
        from_attributes = True


# --- NEW DOMAIN SCHEMAS ---

class QABugResponse(BaseModel):
    id: int
    project_id: int
    project_title: Optional[str] = None
    title: str
    description: str
    severity: str
    status: BugStatus
    reporter_id: int
    reporter_name: Optional[str] = None
    assignee_id: Optional[int] = None
    assignee_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class FinanceRecordResponse(BaseModel):
    id: int
    title: str
    record_type: str
    amount: float
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    date: date
    notes: Optional[str] = None

    class Config:
        from_attributes = True

class ITTicketResponse(BaseModel):
    id: int
    ticket_code: str
    title: str
    description: str
    employee_id: int
    employee_name: Optional[str] = None
    assigned_to_id: Optional[int] = None
    assigned_to_name: Optional[str] = None
    priority: str
    status: TicketStatus
    created_at: datetime

    class Config:
        from_attributes = True

class InventoryAssetResponse(BaseModel):
    id: int
    asset_code: str
    name: str
    category: str
    serial_number: Optional[str] = None
    assigned_to_id: Optional[int] = None
    assigned_to_name: Optional[str] = None
    department_name: Optional[str] = None
    status: str
    purchased_date: date

    class Config:
        from_attributes = True

class DocumentRecordResponse(BaseModel):
    id: int
    title: str
    category: str
    file_name: str
    uploader_id: int
    uploader_name: Optional[str] = None
    confidentiality_level: str
    created_at: datetime

    class Config:
        from_attributes = True

class SalesLeadResponse(BaseModel):
    id: int
    client_name: str
    deal_title: str
    deal_value: float
    stage: str
    assigned_to_id: Optional[int] = None
    assigned_to_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- AI Schemas ---
class AIAssistantQuery(BaseModel):
    query: str
    history: Optional[List[Dict[str, Any]]] = None

class AIAssistantResponse(BaseModel):
    answer: str
    action_type: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class TaskRecommendationRequest(BaseModel):
    task_id: Optional[int] = None
    required_skills: List[str]
    priority: TaskPriority = TaskPriority.MEDIUM

class TaskRecommendationItem(BaseModel):
    employee_id: int
    employee_name: str
    designation: str
    match_score: float
    confidence_score: float
    reasoning: str
    skill_match_percentage: float
    current_workload_level: str

class TaskRecommendationResponse(BaseModel):
    recommendations: List[TaskRecommendationItem]

class BurnoutAnalysisItem(BaseModel):
    employee_id: int
    employee_name: str
    department_name: Optional[str] = None
    designation: Optional[str] = None
    avatar_url: Optional[str] = None
    burnout_score: float
    risk_level: str
    health_status: str = "Stable"
    work_life_balance_score: float = 75.0
    retention_risk: str = "Low"
    fatigue_level: str = "Mild"
    overtime_hours_month: float = 0.0
    late_arrivals_count: int = 0
    pending_tasks_count: int = 0
    overdue_tasks_count: int = 0
    high_priority_tasks_count: int = 0
    completed_tasks_30d: int = 0
    leave_days_taken_last_60d: int = 0
    days_since_last_leave: int = 0
    weekend_work_days: int = 0
    avg_daily_work_hours: float = 8.0
    meetings_count_14d: int = 0
    ai_summary: str = ""
    key_stressors: List[str] = []
    recommendations: List[str] = []
    employee_wellness_tips: List[str] = []
    last_evaluated_at: Optional[str] = None

class BurnoutSummaryResponse(BaseModel):
    total_evaluated: int
    avg_burnout_score: float
    company_work_life_balance: float
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    top_stressors: List[str]
    executive_summary: str

class ReportGenerationRequest(BaseModel):
    report_type: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    department_id: Optional[int] = None
    focus_area: Optional[str] = None

class ReportGenerationResponse(BaseModel):
    report_type: str
    generated_at: datetime
    title: str
    summary: str
    metrics: Dict[str, Any]
    markdown_content: str
    executive_takeaways: List[str] = []
    strategic_recommendations: List[str] = []
    risk_level: str = "NORMAL"


# --- Audit Log Schemas ---
class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


# ==========================================
# Payroll Management Schemas (9 Modules)
# ==========================================

class SalaryStructureCreate(BaseModel):
    employee_id: int
    basic_salary: float
    house_rent_allowance: Optional[float] = 0.0
    medical_allowance: Optional[float] = 0.0
    transport_allowance: Optional[float] = 0.0
    food_allowance: Optional[float] = 0.0
    other_allowances: Optional[float] = 0.0
    provident_fund_rate: Optional[float] = 0.0
    tax_deduction_rate: Optional[float] = 0.0
    bank_name: Optional[str] = None
    bank_account_no: Optional[str] = None
    payment_method: Optional[str] = "BANK"
    mobile_banking_no: Optional[str] = None
    effective_date: Optional[date] = None
    is_active: Optional[bool] = True
    notes: Optional[str] = None


class SalaryStructureResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    department_name: Optional[str] = None
    designation: Optional[str] = None
    basic_salary: float
    house_rent_allowance: float
    medical_allowance: float
    transport_allowance: float
    food_allowance: float
    other_allowances: float
    total_allowances: float
    gross_salary: float
    provident_fund_rate: float
    tax_deduction_rate: float
    bank_name: Optional[str] = None
    bank_account_no: Optional[str] = None
    payment_method: str
    mobile_banking_no: Optional[str] = None
    effective_date: date
    is_active: bool
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class AllowanceConfigCreate(BaseModel):
    name: str
    allowance_type: str = "FIXED"
    value: float
    is_taxable: bool = True
    applies_to: str = "ALL"
    is_active: bool = True
    description: Optional[str] = None


class AllowanceConfigResponse(BaseModel):
    id: int
    name: str
    allowance_type: str
    value: float
    is_taxable: bool
    applies_to: str
    is_active: bool
    description: Optional[str] = None

    class Config:
        from_attributes = True


class BonusConfigCreate(BaseModel):
    title: str
    bonus_type: str = "FESTIVAL"
    calculation_type: str = "PERCENTAGE"
    value: float
    effective_month: Optional[str] = None
    is_active: bool = True
    description: Optional[str] = None


class BonusConfigResponse(BaseModel):
    id: int
    title: str
    bonus_type: str
    calculation_type: str
    value: float
    effective_month: Optional[str] = None
    is_active: bool
    description: Optional[str] = None

    class Config:
        from_attributes = True


class DeductionConfigCreate(BaseModel):
    name: str
    deduction_type: str = "POLICY"
    calculation_type: str = "FORMULA"
    value: float
    is_active: bool = True
    description: Optional[str] = None


class DeductionConfigResponse(BaseModel):
    id: int
    name: str
    deduction_type: str
    calculation_type: str
    value: float
    is_active: bool
    description: Optional[str] = None

    class Config:
        from_attributes = True


class PayrollGenerateRequest(BaseModel):
    month_year: str
    title: Optional[str] = None
    department_id: Optional[int] = None
    include_bonus_id: Optional[int] = None


class PayslipResponse(BaseModel):
    id: int
    batch_id: int
    employee_id: int
    employee_name: Optional[str] = None
    department_name: Optional[str] = None
    designation: Optional[str] = None
    month_year: str

    working_days: int
    present_days: int
    absent_days: int
    late_days: int
    paid_leaves: int
    unpaid_leaves: int
    weekend_days: int
    holiday_days: int
    overtime_hours: float
    overtime_amount: float

    basic_salary: float
    house_rent: float
    medical_allowance: float
    transport_allowance: float
    food_allowance: float
    other_allowance: float
    bonus_amount: float
    bonus_note: Optional[str] = None
    gross_salary: float

    absent_deduction: float
    late_deduction: float
    tax_deduction: float
    provident_fund: float
    loan_installment: float
    advance_adjustment: float
    other_deduction: float
    total_deductions: float

    net_salary: float

    payment_status: str
    payment_method: str
    payment_date: Optional[date] = None
    account_number: Optional[str] = None
    transaction_id: Optional[str] = None
    payment_reference: Optional[str] = None

    class Config:
        from_attributes = True


class PayrollBatchResponse(BaseModel):
    id: int
    batch_month: str
    title: str
    total_employees: int
    total_gross: float
    total_allowances: float
    total_bonuses: float
    total_deductions: float
    total_net_salary: float
    status: str
    created_at: datetime
    payslips: Optional[List[PayslipResponse]] = []

    class Config:
        from_attributes = True


class DisbursementRequest(BaseModel):
    payslip_ids: List[int]
    payment_method: str = "BANK"
    payment_date: Optional[date] = None
    transaction_id: Optional[str] = None
    payment_reference: Optional[str] = None


class PayrollSummaryResponse(BaseModel):
    total_monthly_payout: float
    total_allowances: float
    total_bonuses: float
    total_deductions: float
    total_employees_paid: int
    pending_disbursement_count: int
    pending_disbursement_amount: float
    department_breakdown: List[Dict[str, Any]] = []

