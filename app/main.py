
from fastapi import FastAPI
from app.schemas import RunRequest, RunResponse

app = FastAPI(
    title="Enterprise AI Automation",
    description="Planner and Orchestrator Backend",
    version="1.0.0",
)


@app.get("/")
def home():
    return {
        "message": "Enterprise AI Automation API is running!"
    }


@app.get("/health")
def health_check():
    return {
        "status": "success",
        "details": {"service": "backend"},
        "error": None,
    }


@app.post("/run-request", response_model=RunResponse)
def run_request(request: RunRequest):
    return RunResponse(
        status="success",
        details={
            "user_id": request.user_id,
            "received_request": request.request,
            "message": "Request received successfully"
        },
        error=None,
    )
