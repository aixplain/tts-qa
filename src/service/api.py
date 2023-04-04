import os

from glob import glob
from typing import List

import boto3
from fastapi import FastAPI
from fastapi_sqlalchemy import DBSessionMiddleware
from starlette.middleware.cors import CORSMiddleware

from src.service import db_utils
from src.service.bases import BaseModel, SampleModel, AnnotationModel, AnnotatorModel, DatasetModel
from src.service.models import Annotator, Annotation, Sample, Dataset
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


# list datasets
@app.get("/datasets")
def list_datasets() -> List[DatasetModel]:
    datasets = db_utils.list_datasets()
    # map the datasets to the DatasetModel
    return [DatasetModel(**dataset.to_dict()) for dataset in datasets]


# create a dataset
@app.post("/datasets/{dataset_name}")
def create_dataset(dataset_name: str) -> DatasetModel:
    try:
        dataset = db_utils.create_dataset(dataset_name)
        return DatasetModel(**dataset.to_dict())
    except Exception as e:
        return {"message": "Failed", "error": str(e)}


# list all samples
@app.get("/datasets/{dataset_id}/samples")
def list_samples(dataset_id: int) -> List[SampleModel]:
    samples = db_utils.list_samples(dataset_id)
    # map the samples to the SampleModel
    return [SampleModel(**sample.to_dict()) for sample in samples]


# insert a sample
@app.post("/datasets/{dataset_id}/insert")
def insert_sample(dataset_id: int, sample: SampleModel) -> SampleModel:
    try:
        sample = db_utils.insert_sample(dataset_id, sample)
        return SampleModel(**sample.to_dict())
    except Exception as e:
        return {"message": "Failed", "error": str(e)}


# delete a sample
@app.delete("/samples/{sample_id}")
def delete_sample(dataset_id: int, sample_id: int) -> None:
    try:
        db_utils.delete_sample(sample_id)
        return {"message": "Success"}
    except Exception as e:
        return {"message": "Failed", "error": str(e)}
