# Backend Setup and Execution Guide

This document provides complete instructions for configuring, installing, running, and testing the FastAPI backend service for the **AI-Driven Office Management System**.

---

## Table of Contents
1. [Overview and Tech Stack](#overview-and-tech-stack)
2. [Prerequisites](#prerequisites)
3. [Environment Variables Configuration](#environment-variables-configuration)
4. [Virtual Environment and Installation](#virtual-environment-and-installation)
5. [Database Setup and Seeding](#database-setup-and-seeding)
6. [Running the Application](#running-the-application)
7. [API Documentation and Swagger UI](#api-documentation-and-swagger-ui)
8. [Default Demo Credentials](#default-demo-credentials)
9. [Project Structure](#project-structure)
10. [Troubleshooting and Common Issues](#troubleshooting-and-common-issues)

---

## 1. Overview and Tech Stack

The backend is built with modern, high-performance Python libraries and frameworks:
* **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous, modern Python web API framework)
* **ASGI Server:** [Uvicorn](https://www.uvicorn.org/)
* **Relational Database & ORM:** SQLite with [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
* **NoSQL Database:** MongoDB (via Motor and PyMongo for flexible document storage)
* **Authentication:** JWT (JSON Web Tokens) with Passlib and Bcrypt password hashing
* **AI Engine:** Google Gemini API (`google-genai`) for executive summaries, burnout risk analysis, and smart conversational assistance
* **Data Validation:** Pydantic v2 and Pydantic-Settings

---

## 2. Prerequisites

Ensure your system has the following installed:
* **Python:** 3.10, 3.11, 3.12, or 3.14 (`python3 --version`)
* **pip:** Python Package Manager (`pip --version`)
* **SQLite:** Standard built-in Python library
* **Internet Connection:** Required for MongoDB Atlas and Gemini API endpoints

---

## 3. Environment Variables Configuration (`.env`)

Inside the `backend/` directory, verify or create the `.env` file with the following variables:

```env
# MongoDB Atlas Connection
MONGODB_URL="mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority"
MONGODB_DB_NAME="office_management"

# Google Gemini AI Key
GEMINI_API_KEY="your-gemini-api-key-here"

# (Optional configuration overrides)
# DATABASE_URL="sqlite:///./office_management.db"
# SECRET_KEY="SUPER_SECRET_KEY_ENTERPRISE_OFFICE_MGMT_2026_AI_SYSTEM"
# TIMEZONE="Asia/Dhaka"
```

> **Note:** The SQL database runs on local SQLite (`office_management.db`) by default and does not require an external database service installation.

---

## 4. Virtual Environment and Installation

Follow these steps from your terminal:

### Step 4.1: Navigate to the backend directory
```bash
cd backend
```

### Step 4.2: Create a virtual environment (if not already created)
```bash
python3 -m venv venv
```

### Step 4.3: Activate the virtual environment
* **On Linux / macOS:**
  ```bash
  source venv/bin/activate
  ```
* **On Windows (Command Prompt):**
  ```cmd
  venv\Scripts\activate.bat
  ```
* **On Windows (PowerShell):**
  ```powershell
  venv\Scripts\Activate.ps1
  ```

### Step 4.4: Install dependencies
```bash
pip install -r requirements.txt
```

---

## 5. Database Setup and Seeding

### Run SQLite Migrations
To ensure all required database columns are present:
```bash
python migrate.py
```

### Seed Initial Enterprise Demo Data
To populate demo departments, designations, offices, and sample user profiles:
```bash
python -c "from app.seed import seed_database; seed_database()"
```

---

## 6. Running the Application

Ensure the virtual environment is activated, then execute:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Flags explained:
* `app.main:app`: Loads the FastAPI application instance from `app/main.py`.
* `--reload`: Automatically reloads the server when source code files are modified.
* `--host 0.0.0.0`: Binds to all network interfaces, allowing local and LAN access.
* `--port 8000`: Specifies the port number.

### Running in the background (Linux/macOS):
```bash
nohup venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 &
```

---

## 7. API Documentation and Swagger UI

Once the backend is running, open your web browser:

* **Interactive Swagger UI:** [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
* **ReDoc Interface:** [http://localhost:8000/api/v1/redoc](http://localhost:8000/api/v1/redoc)
* **Service Health Check:** [http://localhost:8000/](http://localhost:8000/)

---

## 8. Default Demo Credentials

All seeded demo accounts use the standard password: `password123`

| Email | Role | Data Scope | Allowed Panels |
| :--- | :--- | :--- | :--- |
| `ceo@office.ai` | Super Admin (CEO) | ALL | All 12 Enterprise Panels |
| `hrhead@office.ai` | Department Head | DEPARTMENT | HR, Payroll, Employees, Attendance |
| `pm@office.ai` | Manager | DEPARTMENT | Projects, Tasks, Meetings, Sprints |
| `devlead@office.ai` | Team Leader | TEAM | Dev, QA, Tasks, Code Reviews |
| `developer@office.ai` | Employee | OWN | Tasks, Self Attendance, Leaves |

---

## 9. Project Structure

```text
backend/
├── app/
│   ├── config.py         # Application settings and environment variables
│   ├── database.py       # SQLAlchemy engine and session factory
│   ├── main.py           # FastAPI application entrypoint and middleware
│   ├── models/           # SQLAlchemy DB models (User, Employee, Task, etc.)
│   ├── mongodb.py        # MongoDB motor client integration
│   ├── routers/          # API route handlers (auth, employees, tasks, ai, etc.)
│   ├── schemas/          # Pydantic schemas for request and response validation
│   ├── security.py       # Password hashing and JWT token management
│   ├── seed.py           # Initial enterprise demo database seeder
│   └── timezone.py       # Standard timezone configuration
├── migrate.py            # SQLite table migration script
├── requirements.txt      # Python dependencies list
├── .env                  # Environment configuration secrets
└── office_management.db  # SQLite database file
```

---

## 10. Troubleshooting and Common Issues

1. **Port 8000 already in use (`Address already in use`):**
   * Check which process is occupying port 8000:
     ```bash
     lsof -i :8000
     ```
   * Terminate the process:
     ```bash
     kill -9 <PID>
     ```

2. **ModuleNotFoundError:**
   * Verify that your virtual environment is active: `source venv/bin/activate`
   * Reinstall dependencies: `pip install -r requirements.txt`

3. **Database locked error (SQLite):**
   * Verify that multiple write operations or redundant server instances are not locking `office_management.db`.
