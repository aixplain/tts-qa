import datetime
from typing import Dict, List

from pydantic import BaseModel, Field
from pydantic_sqlalchemy import sqlalchemy_to_pydantic

from src.service.models import Annotator, Annotation, Sample, Dataset

BaseAnnotatorModel = sqlalchemy_to_pydantic(Annotator)
BaseAnnotationModel = sqlalchemy_to_pydantic(Annotation)
BaseSampleModel = sqlalchemy_to_pydantic(Sample)
BaseDatasetModel = sqlalchemy_to_pydantic(Dataset)


class AnnotatorModel(BaseAnnotatorModel):
    """The annotation model."""

    annotation: List[BaseAnnotationModel] = Field(..., alias="annotations")


class AnnotationModel(BaseAnnotationModel):
    """The annotation model."""

    annotator: BaseAnnotatorModel = Field(..., alias="annotator")
    sample: BaseSampleModel = Field(..., alias="sample")


class SampleModel(BaseSampleModel):
    """The sample model."""

    annotation: List[BaseAnnotationModel] = Field(..., alias="annotations")
    dataset: BaseDatasetModel = Field(..., alias="dataset")


class DatasetModel(BaseDatasetModel):
    """The dataset model."""

    samples: List[BaseSampleModel] = Field(..., alias="samples")
