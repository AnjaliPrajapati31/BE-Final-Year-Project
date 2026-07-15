from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import soil

app = FastAPI(
    title="AI Agriculture API",
    version="1.0.0",
    description="API is running.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(soil.router)


@app.get("/")
def root():
    return {
        "message": "AI Agriculture API Running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }