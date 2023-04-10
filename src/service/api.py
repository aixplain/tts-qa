import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi_sqlalchemy import DBSessionMiddleware
from starlette.middleware.cors import CORSMiddleware

from src.logger import root_logger
from src.paths import paths
from src.service.annotators import router as annotators_router
from src.service.datasets import router as datasets_router
from src.service.samples import router as samples_router


app_logger = root_logger.getChild("api")

BASE_DIR = str(paths.PROJECT_ROOT_DIR.resolve())
# load the .env file
load_dotenv(os.path.join(BASE_DIR, "vars.env"))


app = FastAPI(title="TTS QA", openapi_url="/api/v1/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(DBSessionMiddleware, db_url=os.getenv("POSTGRES_URL"))

app.logger = app_logger

app.include_router(datasets_router)
app.include_router(samples_router)
app.include_router(annotators_router)


@app.get("/")
def read_root():
    return {"message": "Welcome to the TTS QA API"}
