from typing import Optional

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
    error: Optional[str] = Field(default=None, description="The error message")

    class Config:
        schema_extra = {
            "example": {
                "message": "Failed",
                "error": "The dataset does not exist",
            }
        }


class InputAnnotationModel(BaseModel):
    """The input annotation model."""

    annotator_id: int = Field(..., description="The annotator id")
    final_text: str = Field(..., description="The final text")
    final_sentence_type: str = Field(..., description="The final sentence type")
    isRepeated: bool = Field(..., description="The sample is repeated")
    isAccentRight: bool = Field(..., description="The accent is right")
    isPronunciationRight: bool = Field(..., description="The pronunciation is right")
    isClean: bool = Field(..., description="The sample is clean")
    isPausesRight: bool = Field(..., description="The pauses are right")
    isSpeedRight: bool = Field(..., description="The speed is right")
    isConsisent: bool = Field(..., description="The sample is consistent")
    feedback: str = Field(default=None, description="The feedback")
    status: str = Field(default="NotReviewed", description="The status")
