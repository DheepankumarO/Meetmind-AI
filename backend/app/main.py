from fastapi import FastAPI

from backend.app.routers.meetings import router as meetings_router


app = FastAPI(
    title="MeetMind AI API",
    version="0.1.0",
)

app.include_router(meetings_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}