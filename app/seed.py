from datetime import datetime, date, timedelta
from app.database import SessionLocal, engine, Base
from app.models import (
    User, UserRole, Department, Employee, Attendance, AttendanceStatus,
    LeaveRequest, LeaveType, LeaveStatus, Project, ProjectStatus,
    Task, TaskPriority, TaskStatus, TaskComment, Meeting, AuditLog,
    QABugReport, BugStatus, FinanceRecord, ITSupportTicket, TicketStatus,
    InventoryAsset, DocumentRecord, SalesLead
)
from app.security import get_password_hash

ALL_PANELS = [
    "EXECUTIVE", "HR", "PROJECTS", "DEVELOPMENT", "QA", 
    "DESIGN", "FINANCE", "IT_SUPPORT", "SALES", "INVENTORY", 
    "MEETINGS", "DOCUMENTS"
]

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if database already has users
    if db.query(User).first():
        print("Database already seeded.")
        db.close()
        return

    print("Seeding initial 12-Panel Enterprise data...")

    # 1. Create Departments
    dept_eng = Department(name="Software Development", code="DEV", budget=250000.0)
    dept_hr = Department(name="HR & Administration", code="HR", budget=80000.0)
    dept_pm = Department(name="Project Management", code="PM", budget=150000.0)
    dept_qa = Department(name="QA & Testing", code="QA", budget=90000.0)
    dept_fin = Department(name="Finance & Accounts", code="FIN", budget=110000.0)

    db.add_all([dept_eng, dept_hr, dept_pm, dept_qa, dept_fin])
    db.commit()

    # 2. Create Users & Employees for 6 Access Tiers
    users_data = [
        {
            "email": "mdabdullah.ab898@gmail.com",
            "password": "Abd987@#",
            "role": UserRole.SUPER_ADMIN,
            "data_scope": "ALL",
            "allowed_panels": ALL_PANELS,
            "code": "SA-001",
            "first_name": "Abdullah",
            "last_name": "Admin",
            "designation": "Super Administrator",
            "department": dept_pm,
            "salary": 250000.0,
            "skills": ["Executive Leadership", "System Administration", "AI Systems"]
        },
        {
            "email": "ceo@office.ai",
            "password": "password123",
            "role": UserRole.SUPER_ADMIN,
            "data_scope": "ALL",
            "allowed_panels": ALL_PANELS,
            "code": "EMP-001",
            "first_name": "Alexander",
            "last_name": "Vance",
            "designation": "Chief Executive Officer (CEO)",
            "department": dept_pm,
            "salary": 220000.0,
            "skills": ["Executive Leadership", "Strategic Growth", "Product Roadmap"]
        },
        {
            "email": "hrhead@office.ai",
            "password": "password123",
            "role": UserRole.DEPARTMENT_HEAD,
            "data_scope": "DEPARTMENT",
            "allowed_panels": ["EXECUTIVE", "HR", "PROJECTS", "DEVELOPMENT", "QA", "DESIGN", "FINANCE", "IT_SUPPORT", "INVENTORY", "MEETINGS", "DOCUMENTS"],
            "code": "EMP-002",
            "first_name": "Sarah",
            "last_name": "Jenkins",
            "designation": "Head of HR",
            "department": dept_hr,
            "salary": 140000.0,
            "skills": ["HR Policy", "Talent Acquisition", "Employee Wellness"]
        },
        {
            "email": "pm@office.ai",
            "password": "password123",
            "role": UserRole.MANAGER,
            "data_scope": "DEPARTMENT",
            "allowed_panels": ["HR", "PROJECTS", "DEVELOPMENT", "QA", "DESIGN", "IT_SUPPORT", "INVENTORY", "MEETINGS", "DOCUMENTS"],
            "code": "EMP-003",
            "first_name": "David",
            "last_name": "Chen",
            "designation": "Project Manager",
            "department": dept_pm,
            "salary": 135000.0,
            "skills": ["Agile", "Scrum", "Risk Analysis", "Resource Allocation"]
        },
        {
            "email": "devlead@office.ai",
            "password": "password123",
            "role": UserRole.TEAM_LEADER,
            "data_scope": "TEAM",
            "allowed_panels": ["PROJECTS", "DEVELOPMENT", "QA", "DESIGN", "IT_SUPPORT", "INVENTORY", "MEETINGS", "DOCUMENTS"],
            "code": "EMP-004",
            "first_name": "Marcus",
            "last_name": "Brody",
            "designation": "Development Team Lead",
            "department": dept_eng,
            "salary": 145000.0,
            "skills": ["Angular", "TypeScript", "FastAPI", "Python", "Docker"]
        },
        {
            "email": "developer@office.ai",
            "password": "password123",
            "role": UserRole.EMPLOYEE,
            "data_scope": "OWN",
            "allowed_panels": ["PROJECTS", "DEVELOPMENT", "IT_SUPPORT", "INVENTORY", "MEETINGS", "DOCUMENTS"],
            "code": "EMP-005",
            "first_name": "Elena",
            "last_name": "Rostova",
            "designation": "Software Developer",
            "department": dept_eng,
            "salary": 110000.0,
            "skills": ["Python", "FastAPI", "NLP", "Machine Learning"]
        },
        {
            "email": "auditor@office.ai",
            "password": "password123",
            "role": UserRole.SPECIAL_USER,
            "data_scope": "ALL",
            "allowed_panels": ["EXECUTIVE", "HR", "FINANCE", "DOCUMENTS"],  # Auditor Scoped Panels
            "code": "AUD-001",
            "first_name": "Jonathan",
            "last_name": "Price",
            "designation": "External Compliance Auditor",
            "department": dept_fin,
            "salary": 95000.0,
            "skills": ["Financial Audit", "ISO Compliance", "Security Risk"]
        }
    ]

    created_employees = []
    for u in users_data:
        user_obj = User(
            email=u["email"],
            hashed_password=get_password_hash(u["password"]),
            role=u["role"],
            data_scope=u["data_scope"],
            allowed_panels=u["allowed_panels"],
            custom_permissions={"can_view_audit_logs": True} if u["role"] in [UserRole.SUPER_ADMIN, UserRole.SPECIAL_USER] else {},
            is_active=True,
            is_verified=True
        )
        db.add(user_obj)
        db.commit()
        db.refresh(user_obj)

        emp_obj = Employee(
            user_id=user_obj.id,
            employee_code=u["code"],
            first_name=u["first_name"],
            last_name=u["last_name"],
            department_id=u["department"].id,
            designation=u["designation"],
            salary=u["salary"],
            skills=u["skills"],
            emergency_contact={"name": "Family Contact", "phone": "+1-555-0199", "relation": "Spouse"},
            documents=[{"name": "Employment_Contract.pdf", "url": "/docs/contract.pdf"}]
        )
        db.add(emp_obj)
        db.commit()
        db.refresh(emp_obj)
        created_employees.append(emp_obj)

    emp_ceo, emp_hr, emp_pm, emp_tl, emp_dev, emp_auditor = created_employees

    # 3. Create Sample Projects
    proj_1 = Project(
        title="University Management System",
        description="Comprehensive portal for course enrollment, grading & student telemetry.",
        department_id=dept_eng.id,
        project_manager_id=emp_pm.id,
        budget=180000.0,
        status=ProjectStatus.IN_PROGRESS,
        start_date=date.today() - timedelta(days=45),
        end_date=date.today() + timedelta(days=60)
    )

    proj_2 = Project(
        title="HR Portal Modernization",
        description="Migrating legacy portal to Angular 17 and automated leave processing.",
        department_id=dept_hr.id,
        project_manager_id=emp_pm.id,
        budget=50000.0,
        status=ProjectStatus.DELAYED,
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=15)
    )

    db.add_all([proj_1, proj_2])
    db.commit()

    # 4. Create Sample Tasks
    t1 = Task(
        project_id=proj_1.id,
        title="Implement Dynamic RBAC Guard Router",
        description="Build multi-panel intent classifier and token payload validator.",
        assignee_id=emp_dev.id,
        priority=TaskPriority.HIGH,
        due_date=date.today() + timedelta(days=5),
        required_skills=["Python", "FastAPI"],
        progress=85,
        status=TaskStatus.IN_PROGRESS
    )

    t2 = Task(
        project_id=proj_1.id,
        title="Angular Tailwind Glassmorphism UI Shell",
        description="Design responsive sidebar, topbar, and floating AI chat drawer.",
        assignee_id=emp_tl.id,
        priority=TaskPriority.MEDIUM,
        due_date=date.today() + timedelta(days=3),
        required_skills=["Angular", "TypeScript"],
        progress=100,
        status=TaskStatus.DONE
    )

    db.add_all([t1, t2])
    db.commit()

    # 5. Create QA Bug Reports
    b1 = QABugReport(
        project_id=proj_1.id,
        title="Session token expiration modal fails to trigger on HTTP 401",
        description="When JWT token expires, background HTTP requests freeze instead of redirecting to login page.",
        severity="HIGH",
        status=BugStatus.OPEN,
        reporter_id=emp_tl.id,
        assignee_id=emp_dev.id
    )
    b2 = QABugReport(
        project_id=proj_2.id,
        title="Leave request date picker timezone offset bug",
        description="Selecting start date on Sunday converts to Saturday UTC.",
        severity="MEDIUM",
        status=BugStatus.RESOLVED,
        reporter_id=emp_hr.id,
        assignee_id=emp_tl.id
    )
    db.add_all([b1, b2])
    db.commit()

    # 6. Create Finance Records
    f1 = FinanceRecord(title="Client Q3 Milestone Payment - UMS Project", record_type="REVENUE", amount=75000.0, department_id=dept_eng.id, date=date.today() - timedelta(days=5), notes="Received via Wire Transfer")
    f2 = FinanceRecord(title="Monthly Cloud Server Hosting Infrastructure", record_type="EXPENSE", amount=12500.0, department_id=dept_eng.id, date=date.today() - timedelta(days=10), notes="AWS & GCP Monthly Invoices")
    f3 = FinanceRecord(title="Engineering Department Monthly Payroll", record_type="PAYROLL", amount=65000.0, department_id=dept_eng.id, employee_id=emp_dev.id, date=date.today() - timedelta(days=15), notes="Processed via Direct Deposit")
    db.add_all([f1, f2, f3])
    db.commit()

    # 7. Create IT Support Tickets
    tkt1 = ITSupportTicket(ticket_code="TKT-1024", title="MacBook Pro M2 USB-C Hub Faulty", description="External monitor connection flickering constantly.", employee_id=emp_dev.id, assigned_to_id=emp_tl.id, priority="HIGH", status=TicketStatus.IN_PROGRESS)
    tkt2 = ITSupportTicket(ticket_code="TKT-1025", title="VPN Access Configuration for Auditor", description="Provision encrypted VPN profile for External Compliance Audit.", employee_id=emp_auditor.id, assigned_to_id=emp_tl.id, priority="MEDIUM", status=TicketStatus.RESOLVED)
    db.add_all([tkt1, tkt2])
    db.commit()

    # 8. Create Inventory Assets
    ast1 = InventoryAsset(asset_code="LAP-102", name="Apple MacBook Pro 16'' M2 Max", category="Laptop", serial_number="C02GG389Q6W4", assigned_to_id=emp_dev.id, department_id=dept_eng.id, status="ASSIGNED")
    ast2 = InventoryAsset(asset_code="MON-204", name="Dell UltraSharp 27'' 4K Monitor", category="Monitor", serial_number="CN-0H9381-742", assigned_to_id=emp_dev.id, department_id=dept_eng.id, status="ASSIGNED")
    ast3 = InventoryAsset(asset_code="ROU-001", name="Cisco Enterprise Wi-Fi 6 Router", category="Router", serial_number="CSC-99281-X", assigned_to_id=None, department_id=dept_eng.id, status="AVAILABLE")
    db.add_all([ast1, ast2, ast3])
    db.commit()

    # 9. Create Document Records
    doc1 = DocumentRecord(title="Company Information Security Policy 2026", category="Company", file_name="InfoSec_Policy_2026.pdf", uploader_id=emp_ceo.id, confidentiality_level="PUBLIC")
    doc2 = DocumentRecord(title="Executive Financial Audit & Revenue Summary", category="Confidential", file_name="Financial_Audit_Q2_2026.pdf", uploader_id=emp_auditor.id, confidentiality_level="CONFIDENTIAL")
    db.add_all([doc1, doc2])
    db.commit()

    # 10. Create Sales Leads
    s1 = SalesLead(client_name="Apex Healthcare Systems", deal_title="Enterprise Hospital Management Portal", deal_value=250000.0, stage="PROPOSAL", assigned_to_id=emp_ceo.id)
    s2 = SalesLead(client_name="Global Logistics Inc.", deal_title="Fleet Telemetry & Driver App", deal_value=120000.0, stage="CONTRACT", assigned_to_id=emp_pm.id)
    db.add_all([s1, s2])
    db.commit()

    # 11. Create Attendance Records
    for i in range(5):
        d = date.today() - timedelta(days=i)
        if d.weekday() < 5:
            for emp in created_employees:
                att = Attendance(
                    employee_id=emp.id,
                    date=d,
                    check_in=datetime.combine(d, datetime.min.time()) + timedelta(hours=9),
                    check_out=datetime.combine(d, datetime.min.time()) + timedelta(hours=18),
                    work_hours=8.0,
                    overtime_hours=0.0,
                    status=AttendanceStatus.PRESENT
                )
                db.add(att)
    db.commit()

    # 12. Create Meeting
    m1 = Meeting(
        title="Weekly Executive Operations & Enterprise AI Roadmap",
        organizer_id=emp_pm.id,
        scheduled_time=datetime.utcnow() + timedelta(days=1),
        duration_mins=45,
        attendees=[emp_ceo.id, emp_hr.id, emp_pm.id, emp_tl.id, emp_dev.id],
        raw_notes="Reviewed 12-panel system architecture. Agreed on deploying dynamic RBAC permission control hub.",
        ai_summary="Approved 12-panel RBAC permission structure with 6 access tiers and custom auditor access.",
        ai_action_items=[
            {"task": "Deploy Super Admin Permission Control Center in Angular", "owner": "Marcus Brody", "deadline": "Friday"}
        ]
    )
    db.add(m1)

    # 13. Audit Log
    log1 = AuditLog(
        user_id=emp_ceo.user_id,
        action="SYSTEM_INIT_SEED_ENTERPRISE",
        entity_type="SYSTEM",
        entity_id=1,
        details={"message": "12-Panel Enterprise Database seed completed successfully."},
        ip_address="127.0.0.1"
    )
    db.add(log1)

    db.commit()
    db.close()
    print("12-Panel Enterprise Database seed completed successfully!")

def ensure_super_admin(email: str = "mdabdullah.ab898@gmail.com", password: str = "Abd987@#"):
    """
    Ensures the primary Super Admin exists in the database.
    If exists, updates credentials and super admin permissions.
    If not, creates User and Employee records.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        hashed_pwd = get_password_hash(password)
        if not user:
            user = User(
                email=email,
                hashed_password=hashed_pwd,
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                is_verified=True,
                data_scope="ALL",
                allowed_panels=ALL_PANELS,
                custom_permissions={"all": True}
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            emp = db.query(Employee).filter(Employee.user_id == user.id).first()
            if not emp:
                emp = Employee(
                    user_id=user.id,
                    employee_code="SA-001",
                    first_name="Abdullah",
                    last_name="Admin",
                    designation="Super Administrator",
                    salary=250000.0,
                    personal_email=email,
                    skills=["Executive Leadership", "System Administration", "AI Systems"]
                )
                db.add(emp)
                db.commit()
            print(f"[Seed] Super Admin user created: {email}")
        else:
            user.hashed_password = hashed_pwd
            user.role = UserRole.SUPER_ADMIN
            user.is_active = True
            user.is_verified = True
            user.data_scope = "ALL"
            user.allowed_panels = ALL_PANELS
            db.commit()
            print(f"[Seed] Super Admin user updated: {email}")
    except Exception as e:
        db.rollback()
        print(f"[Seed] Error ensuring super admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
    ensure_super_admin()
