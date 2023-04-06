from fastapi import APIRouter


router = APIRouter(prefix="/samples", tags=["samples"])

from src.logger import root_logger
from src.service.bases import InfoModel, SampleModel  # noqa: F401
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
