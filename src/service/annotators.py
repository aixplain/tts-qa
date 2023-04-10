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
@router.post("/{username}")
def create_annotator(username: str, email: str) -> Union[AnnotatorModel, InfoModel]:
    try:
        annotator = db_utils.create_annotator(username=username, email=email)
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
def update_annotator(id: int, username: str, email: str) -> Union[AnnotatorModel, InfoModel]:
    try:
        annotator = {"username": username, "email": email}

        annotator = db_utils.update_annotator(id, **annotator)  # type: ignore
        return AnnotatorModel(**annotator.to_dict())  # type: ignore # noqa: F821
    except Exception as e:
        return InfoModel(**{"message": "Failed", "error": str(e)})
