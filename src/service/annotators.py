from typing import List, Union

from fastapi import APIRouter

from src.logger import root_logger
from src.service.bases import AnnotatorModel, InfoModel, SampleModel  # noqa: F401
from src.utils import db_utils


router = APIRouter(prefix="/annotators", tags=["annotators"])

app_logger = root_logger.getChild("api/annotators")


# list annotators
@router.get("/")
def list_annotators() -> List[AnnotatorModel]:
    annotators = db_utils.list_annotators()
    # map the annotators to the AnnotatorModel
    return [AnnotatorModel(**annotator.to_dict()) for annotator in annotators]


# create an annotator
@router.post("/{name}")
def create_annotator(name: str, description: str = None) -> Union[AnnotatorModel, InfoModel]:
    try:
        annotator = db_utils.create_annotator(name)
        return AnnotatorModel(**annotator.to_dict())
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})


# get annotator
@router.get("/{id}")
def get_annotator_by_id(id: int) -> Union[AnnotatorModel, InfoModel]:
    try:
        annotator = db_utils.get_annotator_by_id(id)
        return AnnotatorModel(**annotator.to_dict())
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})


# delete an annotator
@router.delete("/{id}")
def delete_annotator(id: int) -> Union[AnnotatorModel, InfoModel]:
    try:
        db_utils.delete_annotator(id)
        return InfoModel(**{"message": "Success"})
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})


# update an annotator
@router.put("/{id}")
def update_annotator(id: int, name: str = None, description: str = None) -> Union[AnnotatorModel, InfoModel]:
    try:
        annotator = {"name": name, "description": description}
        annotator = db_utils.update_annotator(id, annotator)
        return AnnotatorModel(**annotator.to_dict())
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})
