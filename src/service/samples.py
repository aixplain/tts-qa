from typing import List

from fastapi import APIRouter


router = APIRouter(prefix="/samples", tags=["samples"])

from src.logger import root_logger
from src.service.bases import InfoModel, InputAnnotationModel, SampleModel  # noqa: F401
from src.utils import db_utils


app_logger = root_logger.getChild("api/samples")


# delete a sample
@router.delete("{id}")
def delete_sample(id: int) -> InfoModel:
    try:
        db_utils.delete_sample(id)
        return InfoModel(**{"message": "Success"})
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})


# list samples
@router.get("/")
def list_samples() -> List[SampleModel]:
    samples = db_utils.list_samples()  # type: ignore
    # map the samples to the SampleModel
    return [SampleModel(**sample.to_dict()) for sample in samples]


# get a sample
@router.get("/{id}")
def get_sample_by_id(id: int) -> SampleModel:
    sample = db_utils.get_sample_by_id(id)
    return SampleModel(**sample.to_dict())


# annotate a sample
@router.put("/{id}")
def annotate_sample(id: int, annotation: InputAnnotationModel) -> InfoModel:
    try:
        db_utils.annotate_sample(sample_id=id, **dict(annotation))
        return InfoModel(**{"message": "Success"})
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})


# lock sample for annotation
@router.put("/{id}/lock")
def lock_sample(id: int) -> InfoModel:
    try:
        db_utils.lock_sample(id)
        return InfoModel(**{"message": "Success"})
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})


# unlock sample for annotation
@router.put("/{id}/unlock")
def unlock_sample(id: int) -> InfoModel:
    try:
        db_utils.unlock_sample(id)
        return InfoModel(**{"message": "Success"})
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})
