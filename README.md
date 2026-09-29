# AI-Driven Office Management System - Backend API

For full setup, configuration, running, and troubleshooting instructions, please see [INSTRUCTIONS.md](file:///home/abdullah/Abdullah/Software%20Developement/backend/INSTRUCTIONS.md).

## Environment Setup

Create a `.env` file in the `backend/` directory with the following variables before starting the server:

```ini
SECRET_KEY="your_secret_key_here"
MONGODB_URL="your_mongodb_connection_string"
MONGODB_DB_NAME="office_management"
GEMINI_API_KEY="your_gemini_api_key_here"
```

## Quick Start
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

* **Swagger Docs:** [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
* **API Root:** [http://localhost:8000/](http://localhost:8000/)
Live Link: pulse-hr-ai.vercel.app
