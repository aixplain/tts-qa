import os
import pdb
import tempfile
from typing import List, Tuple, Union

import numpy as np
from fastapi_sqlalchemy import db
from sqlalchemy import Column, MetaData, Table, Text, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.schema import DropTable
from sqlalchemy.sql import case, delete, select, update

from src.logger import root_logger
from src.paths import paths
from src.service.models import Annotator, Annotation, Sample, Dataset
from dotenv import load_dotenv


BASE_DIR = str(paths.PROJECT_ROOT_DIR.resolve())
# load the .env file
load_dotenv(os.path.join(BASE_DIR, "vars.env"))

app_logger = root_logger.getChild("db_utils")


def create_dataset(dataset_name: str) -> Dataset:
    """Create a dataset in the database.

    Args:
        dataset_name (str): The name of the dataset.

    Returns:
        Dataset: The dataset created.
    """
    app_logger.debug(f"POSTGRES: Creating dataset {dataset_name}")
    with db.session.begin():
        dataset = Dataset(name=dataset_name)
        db.session.add(dataset)
        return dataset



def list_datasets() -> List[Dataset]:
    """List all the datasets in the database.

    Returns:
        List[Dataset]: The list of datasets.
    """
    app_logger.debug("POSTGRES: Listing datasets")
    with db.session.begin():
        return db.session.query(Dataset).all()


def delete_dataset(dataset_id: int) -> None:
    """Delete a dataset from the database.

    Args:
        dataset_id (int): The dataset id to delete.
    """
    app_logger.debug(f"POSTGRES: Deleting dataset {dataset_id}")
    with db.session.begin():
        db.session.query(Dataset).filter(Dataset.id == dataset_id).delete()




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
def insert_sample(dataset_id, sample: Sample) -> None:
    """Insert a sample into the database.

    Args:
        dataset_id (int): The dataset id to insert the sample into.
        sample (Sample): The sample to insert.
    """
    app_logger.debug(f"POSTGRES: Inserting sample {sample.name}")
    with db.session.begin():
        sample.dataset_id = dataset_id
        db.session.add(sample)


def insert_samples(dataset_id: int, samples: List[Sample]) -> None:
    """Insert a list of samples into the database.

    Args:
        dataset_id (int): The dataset id to insert the samples into.
        samples (List[Sample]): The samples to insert.
    """
    app_logger.debug(f"POSTGRES: Inserting {len(samples)} samples")
    with db.session.begin():
        for sample in samples:
            insert_samples(dataset_id, sample)




def delete_sample(sample_id: int) -> None:
    """Delete a sample from the database.

    Args:
        sample_id (int): The sample id to delete.
    """
    app_logger.debug(f"POSTGRES: Deleting sample {sample_id}")
    with db.session.begin():
        db.session.query(Sample).filter(Sample.id == sample_id).delete()

def list_samples(dataset_id: int) -> List[Sample]:
    """List all the samples in the database.

    Args:
        dataset_id (int): The dataset id to list the samples from.

    Returns:
        List[Sample]: The list of samples.
    """
    app_logger.debug(f"POSTGRES: Listing samples for dataset {dataset_id}")
    with db.session.begin():
        return db.session.query(Sample).filter(Sample.dataset_id == dataset_id).all()
