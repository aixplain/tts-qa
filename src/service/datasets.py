import asyncio
from typing import List, Union

from fastapi import APIRouter

from src.logger import root_logger
from src.service.bases import DatasetModel, InfoModel, SampleModel  # noqa: F401
from src.utils import db_utils


router = APIRouter(prefix="/datasets", tags=["datasets"])

app_logger = root_logger.getChild("api/datasets")


# list datasets
@router.get("/")
def list_datasets() -> List[DatasetModel]:
    datasets = db_utils.list_datasets()
    # map the datasets to the DatasetModel
    return [DatasetModel(**dataset.to_dict()) for dataset in datasets]


# create a dataset
@router.post("/{name}")
def create_dataset(name: str, language: str, description: str = None) -> Union[DatasetModel, InfoModel]:
    try:
        dataset = db_utils.create_dataset(name=name, language=language, description=description)
        return DatasetModel(**dataset.to_dict())
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})


# get dataset
@router.get("/{id}")
def get_dataset_by_id(id: int) -> Union[DatasetModel, InfoModel]:
    try:
        dataset = db_utils.get_dataset_by_id(id)
        return DatasetModel(**dataset.to_dict())
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})


# delete a dataset
@router.delete("/{id}")
def delete_dataset(id: int) -> Union[DatasetModel, InfoModel]:
    try:
        db_utils.delete_dataset(id)
        return InfoModel(**{"message": "Success"})
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})


# update a dataset
@router.put("/{id}")
def update_dataset(id: int, name: str = None, language: str = None, description: str = None) -> Union[DatasetModel, InfoModel]:
    try:
        dataset = {"name": name, "language": language, "description": description}
        dataset = db_utils.update_dataset(id, **dataset)  # type: ignore
        return DatasetModel(**dataset.to_dict())  # type: ignore
    except Exception as e:  # type: ignore
        return InfoModel(**{"message": "Failed", "error": str(e)})


# list all samples
@router.get("/{id}/samples")
def list_samples(id: int, top_k=50) -> List[SampleModel]:
    samples = db_utils.list_samples(id, top_k)
    # map the samples to the SampleModel
    return [SampleModel(**sample.to_dict()) for sample in samples]


# insert a sample
@router.post("/{id}/samples")
def insert_sample(id: int, text: str, audio_path: str, sentence_length: int = None, sentence_type: str = "statement") -> Union[SampleModel, InfoModel]:
    if sentence_length is None:
        sentence_length = len(text.split())

    try:
        sample = db_utils.insert_sample(id, text, audio_path, sentence_type, sentence_length)
        return SampleModel(**sample.to_dict())
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})


# query next sample
@router.get("/{id}/next_sample")
def query_next_sample(id: int) -> Union[SampleModel, InfoModel]:
    try:
        sample = db_utils.query_next_sample(id)
        if sample is None:
            return InfoModel(**{"message": "No more samples"})
        return SampleModel(**sample.to_dict())  # type: ignore
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})


def handle_exceptions(task: asyncio.Task):
    if task.exception():
        print(f"An error occurred in the task: {task.exception()}")


@router.get("/{id}/upload_from_csv")
async def upload(id, csv_path: str):
    failed, n_success = await db_utils.upload_wav_samples(id, csv_path)

    return {"failed": failed, "n_success": n_success}
