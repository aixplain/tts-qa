import os
from typing import List

import boto3
import pandas as pd
from dotenv import load_dotenv
from fastapi_sqlalchemy import db
from tqdm import tqdm

from src.logger import root_logger
from src.paths import paths
from src.service.models import Annotation, Annotator, Dataset, Sample  # # noqa: F401
from src.utils.audio import evaluate_audio


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
        db.session.commit()

    return dataset


def list_datasets() -> List[Dataset]:
    """List all the datasets in the database.

    Returns:
        List[Dataset]: The list of datasets.
    """
    app_logger.debug("POSTGRES: Listing datasets")
    with db.session.begin():
        datasets = db.session.query(Dataset).all()
        db.session.commit()

    return datasets


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
        db.session.commit()


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
        dataset = db.session.query(Dataset).filter(Dataset.id == id).first()
        db.session.commit()
    return dataset


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
        db.session.commit()


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
        annotators = db.session.query(Annotator).all()
        db.session.commit()

    return annotators


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
        db.session.commit()
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
        db.session.commit()


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

        annotator = db.session.query(Annotator).filter(Annotator.id == id).first()
        db.session.commit()
    return annotator


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
        db.session.commit()


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
        db.session.commit()


# Insert samples
def insert_sample(
    dataset_id: int,
    wav_path: str,
    text: str,
) -> Sample:
    """Insert a sample in the database.

    Args:
        dataset_id (int): The dataset id.
        wav_path (str): The wav path.
        text (str): The text.

    Returns:
        Sample: The sample inserted.
    """

    app_logger.debug(f"POSTGRES: Inserting sample {wav_path}")
    with db.session.begin():
        # check if the dataset exists
        dataset = db.session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} does not exist")

        # check if the sample already exists
        sample = db.session.query(Sample).filter(Sample.filename == wav_path).first()
        if sample:
            raise ValueError(f"Sample {wav_path} already exists")

        # get the meta data
        meta = evaluate_audio(wav_path)
        sample = Sample(
            dataset_id=dataset_id,
            filename=wav_path,
            s3url=None,
            original_text=text,
            asr_text=None,
            duration=meta["duration"],
            trim_start=None,
            trim_end=None,
            sentence_type=None,
            sentence_length=None,
            sampling_rate=meta["sampling_rate"],
            sample_format=meta["sample_format"],
            isPCM=meta["isPCM"],
            n_channel=meta["n_channel"],
            format=meta["format"],
            peak_volume_db=meta["peak_volume_db"],
            size=meta["size"],
            isValid=meta["isValid"],
        )
        db.session.add(sample)
        db.session.commit()


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
        db.session.commit()


def list_samples(dataset_id: int) -> List[Sample]:
    """List all the samples in the database.

    Args:
        dataset_id (int): The dataset id to list the samples from.

    Returns:
        List[Sample]: The list of samples.
    """
    app_logger.debug(f"POSTGRES: Listing samples for dataset {dataset_id}")
    with db.session.begin():
        # check if the dataset already exists
        dataset = db.session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} does not exist")

        samples = db.session.query(Sample).filter(Sample.id == dataset_id).all()
        db.session.commit()

    return samples


def upload_wav_samples(dataset_id: int, csv_path: str) -> None:

    # get dataset
    dataset = get_dataset_by_id(dataset_id)
    dataset_name = dataset.name
    bucket_name = os.environ.get("S3_BUCKET_NAME")
    dataset_dir = os.environ.get("S3_DATASET_DIR")

    # Simulate a long-running process
    df = pd.read_csv(csv_path)
    df["s3path"] = df["file_name"].apply(lambda x: os.path.join(dataset_dir, dataset_name, x))

    s3 = boto3.client("s3", aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"), aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"))

    for _, row in df.iterrows():
        # check if not there
        # if not s3.head_object(Bucket=bucket_name, Key=row["s3path"])["ResponseMetadata"]["HTTPStatusCode"] == 200:
        s3.upload_file(row["local_path"], bucket_name, row["s3path"])

    # make sure that db is closed
    db.session.close()
    with db.session.begin():
        # Check if the dataset already exists
        dataset = db.session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} does not exist")

        # get_metadata of each sample using evaluate_audio method that return dict
        for i, row in tqdm(df.iterrows(), total=len(df)):
            meta = evaluate_audio(row["local_path"])
            sample = Sample(
                dataset_id=dataset_id,
                filename=row["file_name"],
                s3url=f"s3://{bucket_name}/{row['s3path']}",
                original_text=row["text"],
                asr_text=None,
                duration=meta["duration"],
                trim_start=None,
                trim_end=None,
                sentence_type=row["sentence_type"],
                sentence_length=row["sentence_length"],
                sampling_rate=meta["sampling_rate"],
                sample_format=meta["sample_format"],
                isPCM=meta["isPCM"],
                n_channel=meta["n_channel"],
                format=meta["format"],
                peak_volume_db=meta["peak_volume_db"],
                size=meta["size"],
                isValid=meta["isValid"],
            )

            db.session.add(sample)
        db.session.commit()
    app_logger.info(f"POSTGRES: Uploaded {len(df)} samples to dataset {dataset_id}")
