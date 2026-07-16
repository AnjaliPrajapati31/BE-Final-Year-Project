import os
import logging

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

logging.getLogger('tensorflow').setLevel(logging.ERROR)
logging.getLogger('absl').setLevel(logging.ERROR)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import disease
from app.routers import soil
from app.utils.response import success

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
app.include_router(disease.router)


@app.get("/")
def root():
    return success("AI Agriculture API Running")


@app.get("/health")
def health():
    return success("Service is healthy", {"status": "healthy"})