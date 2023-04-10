import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, func, Integer, MetaData, String, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base(metadata=MetaData())


class Status(enum.Enum):
    Reviewed = "Reviewed"
    Discarded = "Discarded"
    NotReviewed = "NotReviewed"


# Define a Annotator model in qhich we will store the annotators's username and email address
class Annotator(Base):  # type: ignore
    __tablename__ = "annotator"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    annotations = relationship("Annotation", backref="annotator")

    # add unique constraint to username and email
    __table_args__ = (UniqueConstraint("username", "email", name="_username_email_uc"),)

    def __repr__(self):
        return f"{self.to_dict()}"

    def to_dict(self):
        return {"id": self.id, "username": self.username, "email": self.email}


# Define a Sample model in which we will store following nformation for an tts recording sample:
# id, unique filename, s3RawPath, original text, asr text, the duration of the recording, sentence_tyoe,
class Sample(Base):  # type: ignore
    __tablename__ = "sample"
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("dataset.id"))
    filename = Column(String(50), unique=False, nullable=False)
    local_path = Column(String(120), unique=False, nullable=False)
    local_trimmed_path = Column(String(120), unique=False, nullable=True)
    s3RawPath = Column(String(120), unique=True, nullable=False)
    s3TrimmedPath = Column(String(120), unique=True, nullable=True)
    original_text = Column(String(250), unique=False, nullable=False)
    asr_text = Column(String(250), unique=False, nullable=True)
    duration = Column(Float, unique=False, nullable=False)
    trimmed_audio_duration = Column(Float, unique=False, nullable=True)
    sentence_type = Column(String(50), unique=False, nullable=False)
    sentence_length = Column(Integer, unique=False, nullable=False)
    sampling_rate = Column(Integer, unique=False, nullable=False)
    sample_format = Column(String(10), unique=False, nullable=False)
    isPCM = Column(Boolean, unique=False, nullable=False)
    n_channel = Column(Integer, unique=False, nullable=False)
    format = Column(String(10), unique=False, nullable=False)
    peak_volume_db = Column(Float, unique=False, nullable=False)
    size = Column(Integer, unique=False, nullable=False)
    isValid = Column(Boolean, unique=False, nullable=False)
    trim_start = Column(Float, unique=False, nullable=True)
    trim_end = Column(Float, unique=False, nullable=True)
    longest_pause = Column(Float, unique=False, nullable=True)
    wer = Column(Float, unique=False, nullable=True)
    __table_args__ = (
        UniqueConstraint("filename", "s3RawPath", "s3TrimmedPath", name="_filename_s3RawPath_uc"),
    )  # Example for such cases combination of filename and s3RawPath should be unique

    def __repr__(self):
        return f"{self.to_dict()}"

    def to_dict(self):
        return {
            "id": self.id,
            "dataset_id": self.dataset_id,
            "filename": self.filename,
            "local_path": self.local_path,
            "local_trimmed_path": self.local_trimmed_path,
            "s3RawPath": self.s3RawPath,
            "s3TrimmedPath": self.s3TrimmedPath,
            "original_text": self.original_text,
            "duration": self.duration,
            "trimmed_audio_duration": self.trimmed_audio_duration,
            "sentence_type": self.sentence_type,
            "sentence_length": self.sentence_length,
            "sampling_rate": self.sampling_rate,
            "sample_format": self.sample_format,
            "isPCM": self.isPCM,
            "n_channel": self.n_channel,
            "format": self.format,
            "peak_volume_db": self.peak_volume_db,
            "size": self.size,
            "isValid": self.isValid,
            "asr_text": self.asr_text,
            "trim_start": self.trim_start,
            "trim_end": self.trim_end,
            "longest_pause": self.longest_pause,
            "wer": self.wer,
        }


# Define a Annotation Model in which we will store the following information for an annotation:
# id, annotator_id, sample_id, the date and time when the annotation was created and annotation fields
# status Enumeration y defauld it is NULL, Approved, Rejected
# isAccentRight bool default is NULL, True, False
# isPronunciationRight bool default is NULL, True, False
# isTypeRight bool default is NULL, True, False
# isClean bool default is NULL, True, False
# isPausesRight bool default is NULL, True, False
# isSpeedRight bool default is NULL, True, False
# isConsisent bool default is NULL, True, False
# feedback text
class Annotation(Base):  # type: ignore
    __tablename__ = "annotation"
    id = Column(Integer, primary_key=True)
    annotator_id = Column(Integer, ForeignKey("annotator.id"), nullable=False)
    sample_id = Column(Integer, ForeignKey("sample.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    status = Column(Enum(Status), default=Status.NotReviewed)
    final_text = Column(String(250), unique=False, nullable=True)
    isAccentRight = Column(Boolean, default=None, nullable=True)
    isPronunciationRight = Column(Boolean, default=None, nullable=True)
    isTypeRight = Column(Boolean, default=None, nullable=True)
    isClean = Column(Boolean, default=None, nullable=True)
    isPausesRight = Column(Boolean, default=None, nullable=True)
    isSpeedRight = Column(Boolean, default=None, nullable=True)
    isConsisent = Column(Boolean, default=None, nullable=True)
    feedback = Column(String(250), unique=False, nullable=True)

    __table_args__ = (UniqueConstraint("annotator_id", "sample_id", name="_annotator_sample_uc"),)

    def __repr__(self):
        return f"{self.to_dict()}"

    def to_dict(self):
        return {
            "id": self.id,
            "annotator_id": self.annotator_id,
            "sample_id": self.sample_id,
            "created_at": self.created_at,
            "status": self.status,
            "final_text": self.final_text,
            "isAccentRight": self.isAccentRight,
            "isPronunciationRight": self.isPronunciationRight,
            "isTypeRight": self.isTypeRight,
            "isClean": self.isClean,
            "isPausesRight": self.isPausesRight,
            "isSpeedRight": self.isSpeedRight,
            "isConsisent": self.isConsisent,
            "feedback": self.feedback,
        }


# Define a Dataset model in which we will store the following information for a dataset:
# id, name, description, the date and time when the dataset was created, list of sampes in the dataset
class Dataset(Base):  # type: ignore
    __tablename__ = "dataset"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    language = Column(String(5), unique=False, nullable=False)
    description = Column(String(250), unique=False, nullable=True)
    created_at = Column(DateTime, default=func.now())
    samples = relationship("Sample", cascade="all, delete", backref="dataset")

    __table_args__ = (UniqueConstraint("name", name="_name_uc"),)

    def __repr__(self):
        return f"{self.to_dict()}"

    def to_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description, "language": self.language, "created_at": self.created_at}
