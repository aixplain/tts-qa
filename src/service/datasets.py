import asyncio
import traceback
from typing import List, Union

from fastapi import APIRouter

from src.logger import root_logger
from src.service.bases import AnnotationModel, AnnotatorModel, DatasetModel, InfoModel, SampleModel  # noqa: F401
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
def insert_sample(
    id: int, text: str, audio_path: str, sentence_length: int = None, sentence_type: str = "statement", deliverable: str = None
) -> Union[SampleModel, InfoModel]:
    if sentence_length is None:
        sentence_length = len(text.split())

    try:
        sample = db_utils.insert_sample(id, text, audio_path, sentence_type, sentence_length, deliverable=deliverable)
        return SampleModel(**sample.to_dict())
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})


# get annotators allowed to annotate this dataset
@router.get("/{id}/annotators")
def get_annotators_of_dataset(id: int) -> Union[List[AnnotatorModel], InfoModel]:
    try:
        annotators = db_utils.get_annotators_of_dataset(id)
        return [AnnotatorModel(**annotator.to_dict()) for annotator in annotators]
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})


# query next sample
@router.get("/{id}/next_sample")
def query_next_sample(id: int) -> dict:
    try:
        sample, stats = db_utils.query_next_sample(id)
        if sample is None:
            return {"sample": None, "stats": stats}
        return {"sample": SampleModel(**sample.to_dict()), "stats": stats}  # type: ignore
    except Exception as e:
        return {"message": "Failed", "error": str(e)}


# get the annotations of dataset samples
@router.get("/{id}/annotations")
def get_annotations_of_dataset(id: int) -> Union[List[dict], InfoModel]:
    try:
        annotations = db_utils.get_annotations_of_dataset(id)
        return [annotation for annotation in annotations]
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})


def handle_exceptions(task: asyncio.Task):
    if task.exception():
        print(f"An error occurred in the task: {task.exception()}")


from src.service.tasks import segmented_onboarding_job, unsegmented_onboarding_job, unsegmented_onboarding_job_sync


@router.get("/{id}/upload_segmented_async")
def upload_segmented(id, csv_path: str, deliverable: str = None):
    job = segmented_onboarding_job.delay(dataset_id=id, csv_path=csv_path, deliverable=deliverable)
    return {"job_id": job.id}


@router.get("/check_job_status/{job_id}")
def check_job_status(job_id: str):
    job = segmented_onboarding_job.AsyncResult(job_id)
    if job.state == "SUCCESS":
        progress = 100
    elif job.state == "PENDING":
        progress = 0
    else:
        progress = job.info.get("progress", 0)
    if job.info is None:
        return {"status": job.status, "progress": progress, "onboarded_samples": 0, "failed_samples": []}
    return {
        "status": job.status,
        "progress": progress,
        "onboarded_samples": job.info.get("onboarded_samples", 0),
        "failed_samples": job.info.get("failed_samples", []),
    }


@router.get("/{id}/upload_unsegmented_async")
def upload_unsegmented_async(id, wavs_path: str, csv_path: str, start_id_regex: str, end_id_regex: str, deliverable: str = None):
    # get dataset language
    dataset = db_utils.get_dataset_by_id(id)
    job = unsegmented_onboarding_job.delay(
        dataset_id=id,
        language=dataset.language,
        wavs_path=wavs_path,
        csv_path=csv_path,
        start_id_regex=start_id_regex,
        end_id_regex=end_id_regex,
        deliverable=deliverable,
    )
    return {"job_id": job.id}


@router.get("/{id}/upload_unsegmented_sync")
def upload_unsegmented_sync(id, wavs_path: str, csv_path: str, start_id_regex: str, end_id_regex: str, deliverable: str = None):
    # get dataset language

    dataset = db_utils.get_dataset_by_id(id)
    try:
        unsegmented_onboarding_job_sync(
            dataset_id=id,
            language=dataset.language,
            wavs_path=wavs_path,
            csv_path=csv_path,
            start_id_regex=start_id_regex,
            end_id_regex=end_id_regex,
            deliverable=deliverable,
        )
        return {"message": "Success"}
    except Exception as e:
        app_logger.error(f"{traceback.format_exc()}")
        return {"message": "Failed", "error": str(e)}
