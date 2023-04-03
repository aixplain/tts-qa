import os
import pdb
from typing import List, Tuple, Union

import numpy as np
from fastapi_sqlalchemy import db
from sqlalchemy import Column, MetaData, Table, Text, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.schema import DropTable
from sqlalchemy.sql import case, delete, select, update

from src.logger import root_logger
from src.paths import paths
from src.service.models import Annotator, Annotation, Sample
from dotenv import load_dotenv


BASE_DIR = str(paths.PROJECT_ROOT_DIR.resolve())
# load the .env file
load_dotenv(os.path.join(BASE_DIR, "vars.env"))

app_logger = root_logger.getChild("db_utils")

# DBSession = scoped_session(sessionmaker())
# engine = None


# def init_session(postgres_url):
#     global engine, DBSession
#     app_logger.debug(f"POSTGRES: Initializing session")
#     engine = create_engine(postgres_url, echo=False, pool_size=20, max_overflow=0)
#     DBSession.remove()
#     DBSession.configure(bind=engine, autoflush=False, expire_on_commit=False)


# app_logger.debug(os.getenv("POSTGRES_URL"))
# init_session(postgres_url=os.getenv("POSTGRES_URL"))


def update_sample(sample_id: int, **kwargs) -> None:
    """Update a sample in the database.

    Args:
        sample_id (int): The sample id to update.
        **kwargs: The fields to update.
    """
    app_logger.debug(f"POSTGRES: Updating sample {sample_id}")
    with db.session.begin():
        db.session.query(Sample).filter(Sample.id == sample_id).update(kwargs)


# Insert samples
def insert_sample(sample: Sample) -> None:
    """Insert a sample into the database.

    Args:
        sample (Sample): The sample to insert.
    """
    app_logger.debug(f"POSTGRES: Inserting sample {sample.id}")
    with db.session.begin():
        db.session.add(sample)


def delete_sample(sample_id: int) -> None:
    """Delete a sample from the database.

    Args:
        sample_id (int): The sample id to delete.
    """
    app_logger.debug(f"POSTGRES: Deleting sample {sample_id}")
    with db.session.begin():
        db.session.query(Sample).filter(Sample.id == sample_id).delete()


def list_samples() -> List[Sample]:
    """List all samples in the database.

    Returns:
        List[Sample]: A list of samples.
    """
    app_logger.debug(f"POSTGRES: Listing samples")
    with db.session.begin():
        return db.session.query(Sample).all()


def get_sample(sample_id: int) -> Sample:
    """Get a sample from the database.

    Args:
        sample_id (int): The sample id to get.

    Returns:
        Sample: The sample.
    """
    app_logger.debug(f"POSTGRES: Getting sample {sample_id}")
    with db.session.begin():
        return db.session.query(Sample).filter(Sample.id == sample_id).first()


def get_sample_by_name(sample_name: str) -> Sample:
    """Get a sample from the database.

    Args:
        sample_name (str): The sample name to get.

    Returns:
        Sample: The sample.
    """
    app_logger.debug(f"POSTGRES: Getting sample {sample_name}")
    with db.session.begin():
        return db.session.query(Sample).filter(Sample.name == sample_name).first()
