# Enterprise AI Automation

## Features
- LLM-based task planning using Ollama
- Structured multi-step plans
- Agent registry and dependency handling
- JWT-based demo authentication and role checks
- Risk assessment and human approval
- PostgreSQL task and audit logging
- Meeting summarization and email drafting
- Voice-to-text request input

## Run locally
1. Activate the Python virtual environment:
   ```powershell
   .venv\Scripts\activate
   ```
2. Configure the database connection (set `DATABASE_URL` in `.env` if using PostgreSQL, or defaults to SQLite/Postgres as configured).
3. Start Ollama and pull qwen2.5:7b:
   ```powershell
   ollama pull qwen2.5:7b
   ```
4. Install the requirements:
   ```powershell
   pip install -r requirements.txt
   ```
5. Start the FastAPI server:
   ```powershell
   python -m uvicorn backend.main:app --reload
   ```
6. (Optional) Start the React frontend:
   ```powershell
   cd frontend
   npm run dev
   ```

## API
- `GET /health` - Health check endpoint
- `POST /token` - Demo JWT token issuance with role assignment
- `POST /run-request` - Validated request execution pipeline with planning, authorization, and risk assessment
- `POST /tasks/{task_id}/approval` - Admin approval/rejection endpoint for high-risk pending tasks

## Limitations
- Demo authentication is not production-ready.
- Calendar execution is simulated.
- Email drafting does not send messages.
- Browser speech recognition depends on browser support.
