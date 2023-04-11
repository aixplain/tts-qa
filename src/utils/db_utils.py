import os
import shutil
import tempfile
from typing import List, Tuple

import boto3
import pandas as pd
from dotenv import load_dotenv
from fastapi_sqlalchemy import db
from sqlalchemy import not_
from tqdm import tqdm

from src.logger import root_logger
from src.paths import paths
from src.service.models import Annotation, Annotator, Dataset, Sample, Status  # noqa: F401
from src.utils.audio import convert_to_88k, convert_to_mono, evaluate_audio, normalize_audio, trim_audio  # noqa: F401


BASE_DIR = str(paths.PROJECT_ROOT_DIR.resolve())
# load the .env file
load_dotenv(os.path.join(BASE_DIR, "vars.env"))

app_logger = root_logger.getChild("db_utils")
s3_bucket_name = os.environ.get("S3_BUCKET_NAME")
s3_dataset_dir = os.environ.get("S3_DATASET_DIR")


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
        # create paths for the dataset
        dataset_path = paths.LOCAL_BUCKET_DIR / s3_dataset_dir / dataset.name
        dataset_path.mkdir(parents=True, exist_ok=True)

        # raw paths
        raw_path = dataset_path / "raw"
        raw_path.mkdir(parents=True, exist_ok=True)

        # trimmed
        trimmed_path = dataset_path / "trimmed"
        trimmed_path.mkdir(parents=True, exist_ok=True)

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

        dataset = db.session.query(Dataset).filter(Dataset.id == id).first()
        db.session.delete(dataset)
        db.session.commit()

        # delete the dataset folder
        dataset_path = paths.LOCAL_BUCKET_DIR / s3_dataset_dir / dataset.name
        shutil.rmtree(dataset_path)


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


def create_annotator(username: str, email: str) -> Annotator:
    """Create an annotator in the database.

    Args:
        username (str): The username of the annotator.
        email (str): The email of the annotator.

    Returns:
        Annotator: The annotator created.
    """
    app_logger.debug(f"POSTGRES: Creating annotator {username}")
    with db.session.begin():
        # check if the annotator already exists
        annotator = db.session.query(Annotator).filter(Annotator.username == username).first()
        if annotator:
            raise ValueError(f"Annotator {username} already exists")

        annotator = Annotator(username=username, email=email)
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
        # return the updated annotator
        annotator = db.session.query(Annotator).filter(Annotator.id == id).first()


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


def list_samples(dataset_id: int, top_k: int = None) -> List[Sample]:
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
        if top_k:
            samples = db.session.query(Sample).filter(Sample.dataset_id == dataset_id).limit(top_k).all()
        else:
            samples = db.session.query(Sample).filter(Sample.dataset_id == dataset_id).all()

    return samples


def get_sample_by_id(id: int) -> Sample:
    """Get a sample by id.

    Args:
        id (int): The sample id.

    Returns:
        Sample: The sample.
    """
    app_logger.debug(f"POSTGRES: Getting sample {id}")
    with db.session.begin():
        # check if the sample exists
        sample = db.session.query(Sample).filter(Sample.id == id).first()
        if not sample:
            raise ValueError(f"Sample {id} does not exist")

    return sample


def annotate_sample(
    sample_id: int,
    annotator_id: int,
    final_text: str,
    final_sentence_type: str,
    isAccentRight: bool,
    isPronunciationRight: bool,
    isClean: bool,
    isPausesRight: bool,
    isSpeedRight: bool,
    isConsisent: bool,
    feedback: str,
    status: str,
) -> None:
    """Annotate a sample in the database.

    Args:
        sample_id (int): The sample id to annotate.
        annotator_id (int): The annotator id to annotate.
        **kwargs: The fields to update.
    """
    app_logger.debug(f"POSTGRES: Annotating sample {sample_id}")
    with db.session.begin():
        # check if the sample exists
        sample = db.session.query(Sample).filter(Sample.id == sample_id).first()
        if not sample:
            raise ValueError(f"Sample {sample_id} does not exist")

        # check if the annotator exists
        annotator = db.session.query(Annotator).filter(Annotator.id == annotator_id).first()
        if not annotator:
            raise ValueError(f"Annotator {annotator_id} does not exist")

        # create annotation
        annotation = Annotation(
            sample_id=sample_id,
            annotator_id=annotator_id,
            final_text=final_text,
            final_sentence_type=final_sentence_type,
            isAccentRight=isAccentRight,
            isPronunciationRight=isPronunciationRight,
            isClean=isClean,
            isPausesRight=isPausesRight,
            isSpeedRight=isSpeedRight,
            isConsisent=isConsisent,
            feedback=feedback,
            status=Status(status),
        )
        db.session.add(annotation)
        db.session.commit()


def query_next_sample(dataset_id: int) -> List[Sample]:
    """List all the samples in the database.

    Args:
        dataset_id (int): The dataset id to list the samples from.

    Returns:
        List[Sample]: The list of samples.
    """
    # this should query the net sample with highest wer in which  there is no annotation yet by checking the annotation table
    app_logger.debug(f"POSTGRES: Listing samples for dataset {dataset_id}")
    with db.session.begin():
        # check if the dataset already exists
        dataset = db.session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} does not exist")

        # join samples and annotations to get the next sample
        all = (
            db.session.query(Sample, Annotation)
            .outerjoin(Annotation, Sample.id == Annotation.sample_id)
            .filter(Sample.dataset_id == dataset_id)
            .filter(
                not_(
                    (Sample.local_trimmed_path == None)
                    | (Sample.local_path == None)
                    | (Sample.s3TrimmedPath == None)
                    | (Sample.s3RawPath == None)
                    | (Sample.asr_text == None)
                )
            )
            .order_by(Sample.wer.desc())
            .all()
        )

        # filter out the samples that have been annotated
        samples = [sample for sample, annotation in all if annotation is None]

    if len(samples) == 0:
        return None
    return samples[0]  # return the first sample


async def upload_wav_samples(dataset_id: int, csv_path: str) -> Tuple[List[str], int]:

    # get dataset
    dataset = get_dataset_by_id(dataset_id)
    dataset_name = dataset.name
    bucket_name = os.environ.get("S3_BUCKET_NAME")
    dataset_dir = os.environ.get("S3_DATASET_DIR")

    # Simulate a long-running process
    df = pd.read_csv(csv_path)

    df["s3RawPath"] = df["file_name"].apply(lambda x: os.path.join(dataset_dir, dataset_name, "raw", x))

    s3 = boto3.client("s3", aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"), aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"))

    # Check if the dataset already exists
    dataset = db.session.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise ValueError(f"Dataset {dataset_id} does not exist")
    failed = []
    # get_metadata of each sample using evaluate_audio method that return dict
    for i, row in tqdm(df.iterrows(), total=len(df)):
        try:
            # make sure that db is closed
            db.session.close()
            with db.session.begin():
                meta = evaluate_audio(row["local_path"])
                with tempfile.TemporaryDirectory() as tmpdir:
                    filename = os.path.basename(row["local_path"])
                    # pdb.set_trace()
                    local_path = os.path.join(str(paths.LOCAL_BUCKET_DIR.resolve()), row["s3RawPath"])
                    # copy the file to the temp directory
                    shutil.copy(row["local_path"], local_path)
                    if meta["is_88khz"] == False:
                        convert_to_88k(row["local_path"], local_path)

                    if meta["peak_volume_db"] < -6 or meta["peak_volume_db"] > -3:
                        normalize_audio(local_path, local_path)

                    meta = evaluate_audio(local_path)

                    sample = Sample(
                        dataset_id=dataset_id,
                        filename=filename,
                        local_path=local_path,
                        s3RawPath=f"s3://{bucket_name}/{row['s3RawPath']}",
                        s3TrimmedPath=None,
                        original_text=row["text"],
                        asr_text=None,
                        duration=meta["duration"],
                        trim_start=None,
                        trim_end=None,
                        trimmed_audio_duration=None,
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
                        wer=None,
                    )

                    db.session.add(sample)
                    s3.upload_file(row["local_path"], bucket_name, row["s3RawPath"])
                    db.session.commit()
        except Exception as e:
            app_logger.error(f"POSTGRES: Error uploading sample {row['file_name']}: {e}")
            failed.append(row["file_name"])
            continue
    app_logger.info(f"POSTGRES: Failed to upload {len(failed)} samples: {failed}")
    app_logger.info(f"POSTGRES: Successfully uploaded {len(df) - len(failed)} samples")
    return failed, len(df) - len(failed)


def insert_sample(
    dataset_id: int,
    text: str,
    audio_path: str,
    sentence_type: str,
    sentence_length: int,
):
    """Insert a new sample into the database.

    Args:
        dataset_id (int): The dataset id to insert the sample into.
        text (str): The text of the sample.
        audio_path (str): The path to the audio file of the sample.

    Returns:
        Sample: The inserted sample.
    """
    dataset = get_dataset_by_id(dataset_id)
    dataset_name = dataset.name
    bucket_name = os.environ.get("S3_BUCKET_NAME")
    dataset_dir = os.environ.get("S3_DATASET_DIR")
    s3 = boto3.client("s3", aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"), aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"))

    app_logger.debug(f"POSTGRES: Inserting sample for dataset {dataset_id}")
    with db.session.begin():
        # check if the dataset already exists
        dataset = db.session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} does not exist")

        if not os.path.exists(audio_path):
            raise ValueError(f"Audio file {audio_path} does not exist. Please check the path.")

        objectkey = os.path.join(dataset_dir, dataset_name, "raw", audio_path)
        local_path = os.path.join(str(paths.LOCAL_BUCKET_DIR.resolve()), objectkey)
        # preprocess the audio file
        meta = evaluate_audio(audio_path)
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.basename(audio_path)
            # copy the file to the temp directory
            shutil.copy(audio_path, local_path)
            if meta["is_88khz"] == False:
                convert_to_88k(local_path, local_path)

            if meta["peak_volume_db"] < -6 or meta["peak_volume_db"] > -3:
                normalize_audio(local_path, local_path)

            meta = evaluate_audio(local_path)

            sample = Sample(
                dataset_id=dataset_id,
                filename=filename,
                local_path=local_path,
                original_text=text,
                asr_text=None,
                duration=meta["duration"],
                trim_start=None,
                trim_end=None,
                trimmed_audio_duration=None,
                sentence_type=sentence_type,
                sentence_length=sentence_length,
                sampling_rate=meta["sampling_rate"],
                sample_format=meta["sample_format"],
                isPCM=meta["isPCM"],
                n_channel=meta["n_channel"],
                format=meta["format"],
                peak_volume_db=meta["peak_volume_db"],
                size=meta["size"],
                isValid=meta["isValid"],
                wer=None,
            )

            db.session.add(sample)
            s3.upload_file(local_path, bucket_name, objectkey)
            db.session.commit()
