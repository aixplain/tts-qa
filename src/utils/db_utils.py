import os
from typing import List

from dotenv import load_dotenv
from fastapi_sqlalchemy import db

from src.logger import root_logger
from src.paths import paths
from src.service.models import Annotation, Annotator, Dataset, Sample  # # noqa: F401


BASE_DIR = str(paths.PROJECT_ROOT_DIR.resolve())
# load the .env file
load_dotenv(os.path.join(BASE_DIR, "vars.env"))

app_logger = root_logger.getChild("db_utils")


########################
###$ DATASET UTILS #####
########################


def create_dataset(name: str, language: str, description: str) -> Dataset:
    """Create a dataset in the database.

    Args:
        name (str): The name of the dataset.

    Returns:
        Dataset: The dataset created.
    """
    app_logger.debug(f"POSTGRES: Creating dataset {name}")
    with db.session.begin():
        # check if the dataset already exists
        dataset = db.session.query(Dataset).filter(Dataset.name == name).first()
        if dataset:
            raise ValueError(f"Dataset {name} already exists")

        dataset = Dataset(name=name, language=language, description=description)
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


def delete_dataset(id: int) -> None:
    """Delete a dataset from the database.

    Args:
        id (int): The dataset id to delete.
    """
    app_logger.debug(f"POSTGRES: Deleting dataset {id}")
    with db.session.begin():
        # check if the dataset exists
        dataset = db.session.query(Dataset).filter(Dataset.id == id).first()
        if not dataset:
            raise ValueError(f"Dataset {id} does not exist")

        db.session.query(Dataset).filter(Dataset.id == id).delete()


def get_dataset_by_id(id: int) -> Dataset:
    """Get a dataset by id.

    Args:
        id (int): The dataset id to get.

    Returns:
        Dataset: The dataset.
    """
    app_logger.debug(f"POSTGRES: Getting dataset {id}")
    with db.session.begin():
        # check if the dataset exists
        dataset = db.session.query(Dataset).filter(Dataset.id == id).first()
        if not dataset:
            raise ValueError(f"Dataset {id} does not exist")

        return db.session.query(Dataset).filter(Dataset.id == id).first()


def update_dataset(id: int, **kwargs) -> None:
    """Update a dataset in the database.

    Args:
        id (int): The dataset id to update.
        **kwargs: The fields to update.
    """
    app_logger.debug(f"POSTGRES: Updating dataset {id}")
    with db.session.begin():
        # check if the dataset exists
        dataset = db.session.query(Dataset).filter(Dataset.id == id).first()
        if not dataset:
            raise ValueError(f"Dataset {id} does not exist")
        # check if name in kwargs
        if "name" in kwargs:
            # check if the dataset already exists
            dataset = db.session.query(Dataset).filter(Dataset.name == kwargs["name"]).first()
            if dataset:
                raise ValueError(f"Dataset {kwargs['name']} already exists")
        db.session.query(Dataset).filter(Dataset.id == id).update(kwargs)


########################
#### ANNOTATOR UTILS ###
########################


def list_annotators() -> List[Annotator]:
    """List all the annotators in the database.

    Returns:
        List[Annotator]: The list of annotators.
    """
    app_logger.debug("POSTGRES: Listing annotators")
    with db.session.begin():
        return db.session.query(Annotator).all()


def create_annotator(name: str) -> Annotator:
    """Create an annotator in the database.

    Args:
        name (str): The name of the annotator.

    Returns:
        Annotator: The annotator created.
    """
    app_logger.debug(f"POSTGRES: Creating annotator {name}")
    with db.session.begin():
        # check if the annotator already exists
        annotator = db.session.query(Annotator).filter(Annotator.name == name).first()
        if annotator:
            raise ValueError(f"Annotator {name} already exists")

        annotator = Annotator(name=name)
        db.session.add(annotator)
        return annotator


def delete_annotator(id: int) -> None:
    """Delete an annotator from the database.

    Args:
        id (int): The annotator id to delete.
    """
    app_logger.debug(f"POSTGRES: Deleting annotator {id}")
    with db.session.begin():
        # check if the annotator exists
        annotator = db.session.query(Annotator).filter(Annotator.id == id).first()
        if not annotator:
            raise ValueError(f"Annotator {id} does not exist")

        db.session.query(Annotator).filter(Annotator.id == id).delete()


def get_annotator_by_id(id: int) -> Annotator:
    """Get an annotator by id.

    Args:
        id (int): The annotator id to get.

    Returns:
        Annotator: The annotator.
    """
    app_logger.debug(f"POSTGRES: Getting annotator {id}")
    with db.session.begin():
        # check if the annotator exists
        annotator = db.session.query(Annotator).filter(Annotator.id == id).first()
        if not annotator:
            raise ValueError(f"Annotator {id} does not exist")

        return db.session.query(Annotator).filter(Annotator.id == id).first()


def update_annotator(id: int, **kwargs) -> None:
    """Update an annotator in the database.

    Args:
        id (int): The annotator id to update.
        **kwargs: The fields to update.
    """
    app_logger.debug(f"POSTGRES: Updating annotator {id}")
    with db.session.begin():
        # check if the annotator exists
        annotator = db.session.query(Annotator).filter(Annotator.id == id).first()
        if not annotator:
            raise ValueError(f"Annotator {id} does not exist")

        db.session.query(Annotator).filter(Annotator.id == id).update(kwargs)


########################
##### SAMPLE UTILS #####
########################


def update_sample(id: int, **kwargs) -> None:
    """Update a sample in the database.

    Args:
        id (int): The sample id to update.
        **kwargs: The fields to update.
    """
    app_logger.debug(f"POSTGRES: Updating sample {id}")
    with db.session.begin():
        # check if the sample exists
        sample = db.session.query(Sample).filter(Sample.id == id).first()
        if not sample:
            raise ValueError(f"Sample {id} does not exist")

        db.session.query(Sample).filter(Sample.id == id).update(kwargs)


# Insert samples
def insert_sample(id, sample: Sample) -> None:
    """Insert a sample into the database.

    Args:
        id (int): The dataset id to insert the sample into.
        sample (Sample): The sample to insert.
    """
    app_logger.debug(f"POSTGRES: Inserting sample {sample.name}")
    with db.session.begin():
        # check if the dataset already exists
        dataset = db.session.query(Dataset).filter(Dataset.id == id).first()
        if not dataset:
            raise ValueError(f"Dataset {id} does not exist")

        sample.id = id
        db.session.add(sample)


def insert_samples(id: int, samples: List[Sample]) -> None:
    """Insert a list of samples into the database.

    Args:
        id (int): The dataset id to insert the samples into.
        samples (List[Sample]): The samples to insert.
    """
    app_logger.debug(f"POSTGRES: Inserting {len(samples)} samples")
    with db.session.begin():
        # check if the dataset already exists
        dataset = db.session.query(Dataset).filter(Dataset.id == id).first()
        if not dataset:
            raise ValueError(f"Dataset {id} does not exist")

        for sample in samples:
            insert_samples(id, sample)


def delete_sample(id: int) -> None:
    """Delete a sample from the database.

    Args:
        id (int): The sample id to delete.
    """
    app_logger.debug(f"POSTGRES: Deleting sample {id}")
    with db.session.begin():
        # check if the sample exists
        sample = db.session.query(Sample).filter(Sample.id == id).first()
        if not sample:
            raise ValueError(f"Sample {id} does not exist")

        db.session.query(Sample).filter(Sample.id == id).delete()


def list_samples(id: int) -> List[Sample]:
    """List all the samples in the database.

    Args:
        id (int): The dataset id to list the samples from.

    Returns:
        List[Sample]: The list of samples.
    """
    app_logger.debug(f"POSTGRES: Listing samples for dataset {id}")
    with db.session.begin():
        # check if the dataset already exists
        dataset = db.session.query(Dataset).filter(Dataset.id == id).first()
        if not dataset:
            raise ValueError(f"Dataset {id} does not exist")

        return db.session.query(Sample).filter(Sample.id == id).all()
