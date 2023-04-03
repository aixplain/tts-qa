import datetime
from typing import Dict, List

from pydantic import BaseModel, Field


class SampleModel(BaseModel):
    """Sample model."""

    id: int = Field(..., description="The sample id.")
    filename: str = Field(..., description="The sample filename.")
    s3url: str = Field(..., description="The sample s3 url.")
    original_text: str = Field(..., description="The sample original text.")
    asr_text: str = Field(..., description="The sample asr text.")
    duration: float = Field(..., description="The sample duration.")
    sentence_type: str = Field(..., description="The sample sentence type.")
