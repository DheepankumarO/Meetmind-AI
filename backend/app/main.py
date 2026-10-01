from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.database import create_db_and_tables
from backend.app.routers.meetings import router as meetings_router
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(
    _: FastAPI,
) -> AsyncIterator[None]:
    create_db_and_tables()
    yield


app = FastAPI(
    title="MeetMind AI API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meetings_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}