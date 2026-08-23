from fastapi import FastAPI
from database.connection import engine, Base
from database import models
Base.metadata.create_all(bind=engine)
app = FastAPI(title="Sentinel API")


@app.get("/")
def root():
    return {
        "message": "Sentinel API is running",
        "database": "connected",
    }