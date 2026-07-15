from fastapi import FastAPI
from app.routers import crop
from app.routers import soil
from app.routers import disease


app = FastAPI()

app.include_router(crop.router)
app.include_router(soil.router)
app.include_router(disease.router)

@app.get("/")
def home():
    return {
        "message":"Backend Running"
    }