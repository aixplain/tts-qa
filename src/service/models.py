from sqlalchemy import Column, DateTime, ForeignKey, func, Integer, MetaData, String, Enum, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base(metadata=MetaData())  # noqa: N801

# Define a Annotator model in qhich we will store the annotators's username and email address
class Annotator(Base):
    __tablename__ = "annotator"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)

    def __repr__(self):
        return f"Annotator('{self.username}', '{self.email}')"

    def to_dict(self):
        return {"id": self.id, "username": self.username, "email": self.email}


# Define a Sample model in which we will store following nformation for an tts recording sample:
# id, unique filename, s3url, original text, asr text, the duration of the recording, sentence_tyoe,
class Sample(Base):
    __tablename__ = "sample"
    id = Column(Integer, primary_key=True)
    filename = Column(String(50), unique=True, nullable=False)
    s3url = Column(String(120), unique=True, nullable=False)
    original_text = Column(String(120), unique=False, nullable=False)
    asr_text = Column(String(120), unique=False, nullable=True)
    duration = Column(Float, unique=False, nullable=False)
    sentence_type = Column(String(50), unique=False, nullable=False)

    def __repr__(self):
        return f"Sample '{self.filename}' with '{self.original_text}'"

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "s3url": self.s3url,
            "original_text": self.original_text,
            "asr_text": self.asr_text,
            "duration": self.duration,
            "sentence_type": self.sentence_type,
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
class Annotation(Base):
    __tablename__ = "annotation"
    id = Column(Integer, primary_key=True)
    annotator_id = Column(Integer, ForeignKey("annotator.id"), nullable=False)
    sample_id = Column(Integer, ForeignKey("sample.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    status = Column(Enum("Approved", "Rejected", name="status"), default=None, nullable=True)
    isAccentRight = Column(Boolean, default=None, nullable=True)
    isPronunciationRight = Column(Boolean, default=None, nullable=True)
    isTypeRight = Column(Boolean, default=None, nullable=True)
    isClean = Column(Boolean, default=None, nullable=True)
    isPausesRight = Column(Boolean, default=None, nullable=True)
    isSpeedRight = Column(Boolean, default=None, nullable=True)
    isConsisent = Column(Boolean, default=None, nullable=True)
    feedback = Column(String(250), unique=False, nullable=True)

    annotator = relationship("Annotator", backref="annotations")
    sample = relationship("Sample", backref="annotations")

    def __repr__(self):
        return f"Annotation of '{self.annotator_id}' on '{self.sample_id}' at '{self.created_at}"

    def to_dict(self):
        return {
            "id": self.id,
            "annotator_id": self.annotator_id,
            "sample_id": self.sample_id,
            "created_at": self.created_at,
            "status": self.status,
            "isAccentRight": self.isAccentRight,
            "isPronunciationRight": self.isPronunciationRight,
            "isTypeRight": self.isTypeRight,
            "isClean": self.isClean,
            "isPausesRight": self.isPausesRight,
            "isSpeedRight": self.isSpeedRight,
            "isConsisent": self.isConsisent,
            "feedback": self.feedback,
        }
