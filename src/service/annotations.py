from typing import List

from fastapi import APIRouter

from src.logger import root_logger
from src.service.bases import AnnotationModel  # noqa: F401
from src.utils import db_utils


router = APIRouter(prefix="/annotations", tags=["annotations"])

app_logger = root_logger.getChild("api/annotations")

# list annotations
@router.get("/")
def list_annotators() -> List[AnnotationModel]:
    annotations = db_utils.list_annotations()
    # map the annotations to the AnnotationModel
    return [AnnotationModel(**annotation.to_dict()) for annotation in annotations]
