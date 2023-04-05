from fastapi import APIRouter


router = APIRouter(prefix="/samples", tags=["samples"])

from src.logger import root_logger
from src.service import db_utils
from src.service.bases import InfoModel, SampleModel  # noqa: F401


app_logger = root_logger.getChild("api/samples")


# delete a sample
@router.delete("{sample_id}")
def delete_sample(sample_id: int) -> InfoModel:
    try:
        db_utils.delete_sample(sample_id)
        return InfoModel(**{"message": "Success"})  # type: ignore
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})  # type: ignore
