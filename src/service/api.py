import os

from glob import glob
from typing import List

import boto3
from fastapi import FastAPI
from fastapi_sqlalchemy import DBSessionMiddleware
from starlette.middleware.cors import CORSMiddleware

from src.service import db_utils
from src.service.bases import BaseModel, SampleModel
from src.service.models import Annotator, Annotation, Sample
from src.logger import root_logger
from src.utils.utils import s3_link_handler
from src.paths import paths

from dotenv import load_dotenv


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


s3 = boto3.resource(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION"),
)


# list all samples
@app.get("/samples")
def list_samples() -> List[SampleModel]:
    samples = db_utils.list_samples()
    # map the samples to the SampleModel
    return [SampleModel(**sample.to_dict()) for sample in samples]


# Insert samples
@app.post("/samples/insert")
def insert_sample(sample: SampleModel):
    try:
        sample_mapped = Sample(
            id=sample.id,
            filename=sample.filename,
            s3url=sample.s3url,
            original_text=sample.original_text,
            asr_text=sample.asr_text,
            duration=sample.duration,
            sentence_type=sample.sentence_type,
        )
        db_utils.insert_sample(sample_mapped)
        return {"message": "Success"}
    except Exception as e:
        return {"message": "Failed", "error": str(e)}


# Delete samples
@app.post("/samples/delete")
def delete_sample(sample_id: int):
    try:
        db_utils.delete_sample(sample_id)
        return {"message": "Success"}
    except Exception as e:
        return {"message": "Failed", "error": str(e)}
