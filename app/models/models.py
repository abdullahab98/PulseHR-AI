import enum
from datetime import datetime, date, time
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Time, Float,
    ForeignKey, Text, Enum, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    DEPARTMENT_HEAD = "DEPARTMENT_HEAD"
    MANAGER = "MANAGER"
    TEAM_LEADER = "TEAM_LEADER"
    EMPLOYEE = "EMPLOYEE"
    SPECIAL_USER = "SPECIAL_USER"

class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    HALF_DAY = "HALF_DAY"
    LATE = "LATE"
    ON_LEAVE = "ON_LEAVE"

class LeaveType(str, enum.Enum):
    SICK = "SICK"
    CASUAL = "CASUAL"
    ANNUAL = "ANNUAL"
    UNPAID = "UNPAID"

class LeaveStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class ProjectStatus(str, enum.Enum):
    PLANNING = "PLANNING"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    DELAYED = "DELAYED"

class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class TaskStatus(str, enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"

class BugStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class TicketStatus(str, enum.Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    budget = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    employees = relationship("Employee", back_populates="department", foreign_keys="[Employee.department_id]")
    projects = relationship("Project", back_populates="department")


class Office(Base):
    __tablename__ = "offices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False)
    establishment = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    mission = Column(Text, nullable=True)
    vision = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employees = relationship("Employee", back_populates="office")
    designations = relationship("Designation", back_populates="office", cascade="all, delete-orphan")


class Rank(Base):
    __tablename__ = "ranks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    employees = relationship("Employee", back_populates="rank")
    designations = relationship("Designation", back_populates="rank", cascade="all, delete-orphan")


class Designation(Base):
    __tablename__ = "designations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    office_id = Column(Integer, ForeignKey("offices.id"), nullable=True)
    rank_id = Column(Integer, ForeignKey("ranks.id"), nullable=True)
    description = Column(Text, nullable=True)
    permissions = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    office = relationship("Office", back_populates="designations")
    rank = relationship("Rank", back_populates="designations")
    employees = relationship("Employee", back_populates="designation_rel")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.EMPLOYEE, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=True)
    
    # 4-Layer Permission Tokens
    allowed_panels = Column(JSON, default=list)       # e.g. ["EXECUTIVE", "HR", "PROJECTS", ...]
    custom_permissions = Column(JSON, default=dict)   # e.g. {"can_approve_leave": True, "can_edit_projects": True}
    data_scope = Column(String(50), default="OWN")    # "ALL", "DEPARTMENT", "TEAM", "OWN"
    
    created_at = Column(DateTime, default=datetime.utcnow)

    employee_profile = relationship("Employee", back_populates="user", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="user")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    employee_code = Column(String(50), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    office_id = Column(Integer, ForeignKey("offices.id"), nullable=True)
    rank_id = Column(Integer, ForeignKey("ranks.id"), nullable=True)
    designation_id = Column(Integer, ForeignKey("designations.id"), nullable=True)
    designation = Column(String(100), nullable=False)
    salary = Column(Float, default=0.0)
    phone = Column(String(50), nullable=True)
    personal_email = Column(String(150), nullable=True)
    address_info = Column(JSON, default=dict)
    family_info = Column(JSON, default=dict)
    bio = Column(Text, nullable=True)
    skills = Column(JSON, default=list)
    emergency_contact = Column(JSON, default=dict)
    documents = Column(JSON, default=list)
    hire_date = Column(Date, default=date.today)

    user = relationship("User", back_populates="employee_profile")
    department = relationship("Department", back_populates="employees", foreign_keys=[department_id])
    office = relationship("Office", back_populates="employees")
    rank = relationship("Rank", back_populates="employees")
    designation_rel = relationship("Designation", back_populates="employees")

    attendance_records = relationship("Attendance", back_populates="employee")
    leave_requests = relationship("LeaveRequest", back_populates="employee", foreign_keys="[LeaveRequest.employee_id]")
    assigned_tasks = relationship("Task", back_populates="assignee")
    managed_projects = relationship("Project", back_populates="project_manager")



class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, default=date.today, nullable=False)
    check_in = Column(DateTime, nullable=True)
    check_out = Column(DateTime, nullable=True)
    work_hours = Column(Float, default=0.0)
    overtime_hours = Column(Float, default=0.0)
    status = Column(Enum(AttendanceStatus), default=AttendanceStatus.PRESENT)

    employee = relationship("Employee", back_populates="attendance_records")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type = Column(Enum(LeaveType), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING)
    approved_by_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", foreign_keys=[employee_id], back_populates="leave_requests")
    approver = relationship("Employee", foreign_keys=[approved_by_id])


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    project_manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    budget = Column(Float, default=0.0)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.PLANNING)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    department = relationship("Department", back_populates="projects")
    project_manager = relationship("Employee", back_populates="managed_projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    assignee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    due_date = Column(Date, nullable=True)
    required_skills = Column(JSON, default=list)
    progress = Column(Integer, default=0)
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO)
    dependencies = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="tasks")
    assignee = relationship("Employee", back_populates="assigned_tasks")
    comments = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")


class TaskComment(Base):
    __tablename__ = "task_comments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="comments")
    author = relationship("Employee")


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    organizer_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    duration_mins = Column(Integer, default=30)
    attendees = Column(JSON, default=list)
    raw_notes = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    ai_action_items = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    organizer = relationship("Employee")


# --- NEW ENTERPRISE PANEL DOMAIN MODELS ---

class QABugReport(Base):
    __tablename__ = "qa_bug_reports"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(50), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(Enum(BugStatus), default=BugStatus.OPEN)
    reporter_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
    reporter = relationship("Employee", foreign_keys=[reporter_id])
    assignee = relationship("Employee", foreign_keys=[assignee_id])


class FinanceRecord(Base):
    __tablename__ = "finance_records"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    record_type = Column(String(50), nullable=False)  # REVENUE, EXPENSE, PAYROLL
    amount = Column(Float, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    date = Column(Date, default=date.today)
    notes = Column(Text, nullable=True)

    department = relationship("Department")
    employee = relationship("Employee")


class ITSupportTicket(Base):
    __tablename__ = "it_tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_code = Column(String(50), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    priority = Column(String(50), default="MEDIUM")
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", foreign_keys=[employee_id])
    assigned_to = relationship("Employee", foreign_keys=[assigned_to_id])


class InventoryAsset(Base):
    __tablename__ = "inventory_assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)  # Laptop, Desktop, Monitor, Keyboard, Router
    serial_number = Column(String(100), nullable=True)
    assigned_to_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    status = Column(String(50), default="ASSIGNED")  # AVAILABLE, ASSIGNED, UNDER_REPAIR
    purchased_date = Column(Date, default=date.today)

    assigned_to = relationship("Employee")
    department = relationship("Department")


class DocumentRecord(Base):
    __tablename__ = "document_records"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)  # Company, HR, Finance, Project, Technical, Confidential
    file_name = Column(String(200), nullable=False)
    uploader_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    confidentiality_level = Column(String(50), default="PUBLIC")  # PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
    created_at = Column(DateTime, default=datetime.utcnow)

    uploader = relationship("Employee")


class SalesLead(Base):
    __tablename__ = "sales_leads"

    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String(150), nullable=False)
    deal_title = Column(String(200), nullable=False)
    deal_value = Column(Float, default=0.0)
    stage = Column(String(50), default="PROSPECT")  # PROSPECT, PROPOSAL, CONTRACT, WON, LOST
    assigned_to_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    assigned_to = relationship("Employee")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(Integer, nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")


class AIInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(String(50), nullable=False)
    target_id = Column(Integer, nullable=True)
    insight_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class TimeSlot(Base):
    __tablename__ = "attendance_time_slots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    start_time = Column(String(20), nullable=False)
    end_time = Column(String(20), nullable=False)
    late_grace_minutes = Column(Integer, default=15)
    is_active = Column(Boolean, default=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AttendanceApplication(Base):
    __tablename__ = "attendance_applications"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, default=date.today, nullable=False)
    requested_check_in = Column(String(50), nullable=True)
    requested_check_out = Column(String(50), nullable=True)
    application_type = Column(String(50), default="Correction")
    reason = Column(Text, nullable=False)
    status = Column(String(20), default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee")


class TimeSlotApplication(Base):
    __tablename__ = "time_slot_applications"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    time_slot_id = Column(Integer, ForeignKey("attendance_time_slots.id"), nullable=False)
    effective_from = Column(Date, default=date.today, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee")
    time_slot = relationship("TimeSlot")


class WeekendSetup(Base):
    __tablename__ = "weekend_setups"

    id = Column(Integer, primary_key=True, index=True)
    days = Column(JSON, default=lambda: ["Friday", "Saturday"])
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    note = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class LeaveTypeConfig(Base):
    __tablename__ = "leave_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(20), nullable=False, unique=True)
    days_allowed = Column(Integer, default=15, nullable=False)
    is_paid = Column(Boolean, default=True)
    requires_attachment = Column(Boolean, default=False)
    carry_forward = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DesignationChain(Base):
    __tablename__ = "designation_chains"

    id = Column(Integer, primary_key=True, index=True)
    designation_id = Column(Integer, ForeignKey("designations.id"), nullable=False)
    approver_designation_id = Column(Integer, ForeignKey("designations.id"), nullable=False)
    level = Column(Integer, default=1)
    auto_approve_days = Column(Integer, default=3)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    designation = relationship("Designation", foreign_keys=[designation_id])
    approver_designation = relationship("Designation", foreign_keys=[approver_designation_id])


# ==========================================
# Payroll Management Models (9 Enterprise Modules)
# ==========================================

class SalaryStructure(Base):
    __tablename__ = "salary_structures"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), unique=True, nullable=False)
    basic_salary = Column(Float, default=0.0, nullable=False)
    house_rent_allowance = Column(Float, default=0.0)
    medical_allowance = Column(Float, default=0.0)
    transport_allowance = Column(Float, default=0.0)
    food_allowance = Column(Float, default=0.0)
    other_allowances = Column(Float, default=0.0)
    provident_fund_rate = Column(Float, default=0.0)
    tax_deduction_rate = Column(Float, default=0.0)
    bank_name = Column(String(100), nullable=True)
    bank_account_no = Column(String(100), nullable=True)
    payment_method = Column(String(50), default="BANK")
    mobile_banking_no = Column(String(50), nullable=True)
    effective_date = Column(Date, default=date.today, nullable=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", backref="salary_structure", uselist=False)


class AllowanceConfig(Base):
    __tablename__ = "allowance_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    allowance_type = Column(String(50), default="FIXED")
    value = Column(Float, default=0.0)
    is_taxable = Column(Boolean, default=True)
    applies_to = Column(String(50), default="ALL")
    is_active = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BonusConfig(Base):
    __tablename__ = "bonus_configs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    bonus_type = Column(String(50), default="FESTIVAL")
    calculation_type = Column(String(50), default="PERCENTAGE")
    value = Column(Float, default=100.0)
    effective_month = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DeductionConfig(Base):
    __tablename__ = "deduction_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    deduction_type = Column(String(50), default="POLICY")
    calculation_type = Column(String(50), default="FORMULA")
    value = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PayrollBatch(Base):
    __tablename__ = "payroll_batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_month = Column(String(20), nullable=False)
    title = Column(String(150), nullable=False)
    total_employees = Column(Integer, default=0)
    total_gross = Column(Float, default=0.0)
    total_allowances = Column(Float, default=0.0)
    total_bonuses = Column(Float, default=0.0)
    total_deductions = Column(Float, default=0.0)
    total_net_salary = Column(Float, default=0.0)
    status = Column(String(50), default="DRAFT")
    generated_by_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_by_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    payslips = relationship("Payslip", back_populates="batch", cascade="all, delete-orphan")


class Payslip(Base):
    __tablename__ = "payslips"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("payroll_batches.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    month_year = Column(String(20), nullable=False)

    working_days = Column(Integer, default=30)
    present_days = Column(Integer, default=0)
    absent_days = Column(Integer, default=0)
    late_days = Column(Integer, default=0)
    paid_leaves = Column(Integer, default=0)
    unpaid_leaves = Column(Integer, default=0)
    weekend_days = Column(Integer, default=0)
    holiday_days = Column(Integer, default=0)
    overtime_hours = Column(Float, default=0.0)
    overtime_amount = Column(Float, default=0.0)

    basic_salary = Column(Float, default=0.0)
    house_rent = Column(Float, default=0.0)
    medical_allowance = Column(Float, default=0.0)
    transport_allowance = Column(Float, default=0.0)
    food_allowance = Column(Float, default=0.0)
    other_allowance = Column(Float, default=0.0)
    bonus_amount = Column(Float, default=0.0)
    bonus_note = Column(String(150), nullable=True)
    gross_salary = Column(Float, default=0.0)

    absent_deduction = Column(Float, default=0.0)
    late_deduction = Column(Float, default=0.0)
    tax_deduction = Column(Float, default=0.0)
    provident_fund = Column(Float, default=0.0)
    loan_installment = Column(Float, default=0.0)
    advance_adjustment = Column(Float, default=0.0)
    other_deduction = Column(Float, default=0.0)
    total_deductions = Column(Float, default=0.0)

    net_salary = Column(Float, default=0.0)

    payment_status = Column(String(50), default="PENDING")
    payment_method = Column(String(50), default="BANK")
    payment_date = Column(Date, nullable=True)
    account_number = Column(String(100), nullable=True)
    transaction_id = Column(String(100), nullable=True)
    payment_reference = Column(String(150), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", backref="payslips")
    batch = relationship("PayrollBatch", back_populates="payslips")


