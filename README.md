# AI-Driven Office Management System — Backend API

An enterprise-grade, asynchronous RESTful API powering an intelligent, end-to-end workforce management ecosystem. Built with **FastAPI**, **SQLAlchemy**, **MongoDB**, and integrated with **Google Gemini AI** for predictive analytics, burnout detection, and executive decision support.

---

## 📌 Project Overview

Traditional Enterprise Resource Planning (ERP) and HR tools often operate in disconnected silos—attendance is tracked in one place, payroll in spreadsheets, project tasks in another, and employee burnout is rarely caught before resignations occur.

This backend provides a unified, **admin-less, designation-driven** architecture where authorization, workflows, and data visibility are dynamically governed by organizational hierarchy (Designations, Ranks, and Branch Offices). It combines deterministic operational engines (Attendance, Payroll, Leaves) with advanced Generative AI capabilities for real-time business intelligence.

---

## 🚀 Key Feature Modules

### 1. 👥 Human Resources (HR) & Designation-Driven Governance
* **Admin-Less Authorization:** Eliminates the static "Super Admin" security risk. All user permissions, panel access, and data scopes (`OWN`, `TEAM`, `DEPARTMENT`, `ALL`) are dynamically derived from the employee's **Designation** and numerical **Rank**.
* **10-Domain System Panel Matrix:** Centralized permission schema controlling granular actions (`view`, `create`, `edit`, `delete`) across 25+ enterprise panels.
* **Hierarchical Approval Chains (`DesignationChain`):** Multi-level approval escalation (Level 1, Level 2) that dynamically routes requests to designated supervisors with auto-approval timeout timers.
* **Multi-Branch Isolation:** Full multi-office support allowing centralized corporate oversight while isolating regional branch data.

### 2. ⏱️ Smart Attendance Tracking Engine
* **Automated Clock-In / Clock-Out:** Records precise check-in and check-out timestamps with real-time status resolution (`PRESENT`, `LATE`, `HALF_DAY`, `ABSENT`).
* **Duration & Overtime Calculation:** Automatically computes daily working hours, overtime hours, and flags weekend shifts (Friday/Saturday).
* **Late Arrival Penalty Integration:** Configurable grace periods and late thresholds that feed directly into the payroll deduction pipeline.
* **Monthly Telemetry:** Aggregates monthly attendance rates and work-hour metrics for HR reporting and AI burnout analysis.

### 3. 🏖️ Leave Management & Approval Workflows
* **Multi-Category Leave Balances:** Supports diverse leave types including Sick Leave, Casual Leave, Annual Leave, Maternity/Paternity Leave, and Unpaid Leave.
* **Self-Service Application Flow:** Employees submit leave requests with date ranges, reasons, and emergency contact details.
* **Designation-Based Approvals:** Requests route through the `DesignationChain` to authorized supervisors for one-click approval or rejection with feedback remarks.
* **Payroll Synchronization:** Approved unpaid leaves automatically adjust monthly payable days and calculate salary deductions.

### 4. 💰 Automated Smart Payroll Engine
* **1-Click Monthly Salary Run:** Automatically reconciles Base Salary + Allowances (House Rent, Medical, Transport, Food) + Overtime Pay − Late Penalties − Unpaid Leaves − Tax/Provident Fund.
* **3-Stage State Machine:** Strict transactional lifecycle: `DRAFT` ➔ `APPROVED` ➔ `PAID`. Once marked as `PAID`, all attendance records and leave data for the period are permanently locked to prevent retroactive tampering or duplicate payouts.
* **Audit-Proof payslip Data:** Generates complete itemized salary structures ready for instant PDF payslip rendering on the frontend.

### 5. 🔥 Predictive Burnout Risk Radar (AI Analytics)
* **30-Day Multi-Vector Telemetry:** Gathers objective workload signals including 30-day overtime hours, average daily work durations, late arrival trends, weekend shifts, and overdue high-priority task backlogs.
* **Quantitative Risk Scoring (0–100):** Normalizes fatigue metrics into four clear risk bands: **Low**, **Moderate**, **High**, and **Critical**.
* **Proactive AI Root-Cause Analysis:** Leverages Google Gemini to explain the primary drivers behind employee exhaustion and suggest actionable workload rebalancing strategies before attrition occurs.

### 6. 🧠 Google Gemini AI Integration & Optimization
* **High-Speed Model Architecture:** Powered by `gemini-3.5-flash-lite` for ultra-fast, sub-second inference (< 1.5s).
* **Multi-Model Fallback Cascade:** Dynamic failover queue (`gemini-3.5-flash-lite` ➔ `gemini-flash-latest` ➔ `gemini-3.5-flash`) guaranteeing zero request timeouts during cloud quota spikes.
* **In-Memory Telemetry Caching (`_METRICS_CACHE`):** Pre-aggregated enterprise metrics are cached for 30 seconds, eliminating redundant database scans and slashing token costs.
* **Strict Token & Temperature Budgeting:** Capped at `max_output_tokens=700` and `temperature=0.6` to deliver crisp, hallucination-free executive summaries without conversational noise.
* **Context-Aware AI Assistant & Report Generator:** Conversational agent capable of answering natural-language queries about office operations, recommending optimal staff for new tasks based on workload, and generating 1-click executive summaries.
* **Local Heuristic Fallback:** If internet or external APIs disconnect, an internal rule-based engine generates immediate summaries, ensuring **100% platform uptime**.

---

## 🛠️ Technology Stack

* **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (High-performance, asynchronous Python Web framework)
* **ASGI Web Server:** [Uvicorn](https://www.uvicorn.org/)
* **Relational Database & ORM:** SQLite / PostgreSQL with [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
* **Document Database:** MongoDB Atlas via [Motor](https://motor.readthedocs.io/) & [PyMongo](https://pymongo.readthedocs.io/)
* **AI Engine:** Google Gemini Flash Lite via [google-genai](https://pypi.org/project/google-genai/) SDK
* **Authentication & Cryptography:** JWT (`PyJWT`), Passlib, and salted `bcrypt`
* **Data Validation:** [Pydantic v2](https://docs.pydantic.dev/) & `pydantic-settings`
* **Testing:** `pytest`, `httpx` (FastAPI TestClient), and Python `unittest`

---

## ⚙️ Environment Configuration (`.env`)

Create a `.env` file in the `backend/` directory with the following configuration:

```ini
# Application Secrets
SECRET_KEY="SUPER_SECRET_KEY_ENTERPRISE_OFFICE_MGMT_2026_AI_SYSTEM"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database Configuration (Defaults to SQLite office_management.db)
DATABASE_URL="sqlite:///./office_management.db"

# MongoDB Connection (For unstructured documents and logs)
MONGODB_URL="mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority"
MONGODB_DB_NAME="office_management"

# Google Gemini AI API Key
GEMINI_API_KEY="your_google_gemini_api_key_here"

# Operational Timezone
TIMEZONE="Asia/Dhaka"
```

---

## 🚦 Quick Start Guide

### 1. Set Up Virtual Environment
```bash
cd backend
python3 -m venv venv
source venv/bin/activate       # On Linux / macOS
# or: venv\Scripts\activate     # On Windows
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Database Migrations & Seed Initial Data
```bash
# Verify SQLite table schemas
python migrate.py

# Seed default offices, ranks, designations, and sample accounts
python -c "from app.seed import seed_database; seed_database()"
```

### 4. Start the Backend API Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📖 API Documentation & Endpoints

Once the server is running, explore the interactive documentation:

* **Interactive Swagger UI:** [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
* **ReDoc Documentation:** [http://localhost:8000/api/v1/redoc](http://localhost:8000/api/v1/redoc)
* **API Health Check:** [http://localhost:8000/](http://localhost:8000/)
* **Live Link:** [pulse-hr-ai.vercel.app](https://pulse-hr-ai.vercel.app/)

### Primary Endpoint Prefixes:
| Prefix | Description |
| :--- | :--- |
| `/api/v1/auth` | Authentication, JWT login, and profile fetching |
| `/api/v1/employees` | Employee lifecycle, salary mapping, and organograms |
| `/api/v1/offices` | Multi-branch office management and regional settings |
| `/api/v1/designations` | Designation hierarchy, RBAC matrix, and approval chains |
| `/api/v1/attendance` | Clock-in/out, daily time slots, overtime, and monthly logs |
| `/api/v1/leaves` | Leave applications, balance tracking, and approvals |
| `/api/v1/payroll` | Salary structures, monthly calculation runs, and disbursements |
| `/api/v1/ai` | Gemini assistant, burnout risk radar, and executive reports |
| `/api/v1/projects` & `/tasks` | Project milestones, task boards, and workload tracking |
| `/api/v1/finance` | Company revenue, operational expenses, and balance sheets |
| `/api/v1/audit-logs` | Compliance tracking and administrative action audit trails |

---

## 🔑 Default Demo Accounts

All seeded demo accounts are provisioned with the standard password: `password123`

| Role / Designation | Demo Email | Access Scope |
| :--- | :--- | :--- |
| **Managing Director** | `md@company.com` | Full Enterprise Scope (`ALL`) |
| **HR Manager** | `hr@company.com` | HR, Attendance, Leaves, Designations |
| **Finance Director** | `finance@company.com` | Payroll, Expenses, Invoices, Disbursement |
| **Engineering Lead** | `techlead@company.com` | Projects, Sprints, QA Bug Tracking |
| **Staff Employee** | `employee@company.com` | Personal Attendance, Leave Portal, Tasks |
