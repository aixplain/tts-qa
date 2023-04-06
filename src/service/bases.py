from typing import Union

from pydantic import BaseModel, Field
from pydantic_sqlalchemy import sqlalchemy_to_pydantic

from src.service.models import Annotation, Annotator, Dataset, Sample


BaseAnnotatorModel = sqlalchemy_to_pydantic(Annotator)
BaseAnnotationModel = sqlalchemy_to_pydantic(Annotation)
BaseSampleModel = sqlalchemy_to_pydantic(Sample)
BaseDatasetModel = sqlalchemy_to_pydantic(Dataset)


class AnnotatorModel(BaseAnnotatorModel):  # type: ignore
    """The annotation model."""

    pass


class AnnotationModel(BaseAnnotationModel):  # type: ignore
    """The annotation model."""

    pass


class SampleModel(BaseSampleModel):  # type: ignore
    """The sample model."""

    pass


class DatasetModel(BaseDatasetModel):  # type: ignore
    """The dataset model."""

    pass


class InfoModel(BaseModel):
    """The error model."""

    message: str = Field(..., description="The error message")
    # error field might be empty or contain the error message
    error: str = Field(None, description="The error message")

    class Config:
        schema_extra = {
            "example": {
                "message": "Failed",
                "error": "The dataset does not exist",
            }
        }
