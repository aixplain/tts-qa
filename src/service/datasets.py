from typing import List, Union

from fastapi import APIRouter

from src.logger import root_logger
from src.service import db_utils
from src.service.bases import DatasetModel, InfoModel, SampleModel


router = APIRouter(prefix="/datasets", tags=["datasets"])

app_logger = root_logger.getChild("api/datasets")


# list datasets
@router.get("/")
def list_datasets() -> List[DatasetModel]:
    datasets = db_utils.list_datasets()
    # map the datasets to the DatasetModel
    return [DatasetModel(**dataset.to_dict()) for dataset in datasets]


# create a dataset
@router.post("/{dataset_name}")
def create_dataset(dataset_name: str, description: str = None) -> Union[DatasetModel, InfoModel]:
    try:
        dataset = db_utils.create_dataset(dataset_name, description)
        return DatasetModel(**dataset.to_dict())
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})  # type: ignore


# get dataset
@router.get("/{dataset_id}")
def get_dataset_by_id(dataset_id: int) -> Union[DatasetModel, InfoModel]:
    try:
        dataset = db_utils.get_dataset_by_id(dataset_id)
        return DatasetModel(**dataset.to_dict())
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})  # type: ignore


# delete a dataset
@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: int) -> Union[DatasetModel, InfoModel]:
    try:
        db_utils.delete_dataset(dataset_id)
        return InfoModel(**{"message": "Success"})  # type: ignore
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})  # type: ignore


# list all samples
@router.get("/{dataset_id}/samples")
def list_samples(dataset_id: int) -> List[SampleModel]:
    samples = db_utils.list_samples(dataset_id)
    # map the samples to the SampleModel
    return [SampleModel(**sample.to_dict()) for sample in samples]
