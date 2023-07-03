import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple

import boto3
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from celery import Task
from dotenv import load_dotenv
from fastapi_sqlalchemy import db
from sqlalchemy import not_
from sqlalchemy.sql.expression import func
from tqdm import tqdm
from yaml.loader import SafeLoader

from src.logger import root_logger
from src.paths import paths
from src.service.models import Annotation, Annotator, Dataset, Sample, Status  # noqa: F401
from src.utils.audio import convert_to_88k, convert_to_mono, convert_to_s16le, evaluate_audio, normalize_audio, trim_audio  # noqa: F401


BASE_DIR = str(paths.PROJECT_ROOT_DIR.resolve())
# load the .env file
load_dotenv(os.path.join(BASE_DIR, "vars.env"))

app_logger = root_logger.getChild("db_utils")
s3_bucket_name = os.environ.get("S3_BUCKET_NAME")
s3_dataset_dir = os.environ.get("S3_DATASET_DIR")


# get engine from url
POSTGRES_URL = os.getenv("POSTGRES_URL")


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


engine = create_engine(POSTGRES_URL)
SessionObject = sessionmaker(bind=engine)
session = SessionObject()


def generate_password_hash(password: str) -> str:
    """Generate a password hash.

    Args:
        password (str): The password to hash.

    Returns:
        str: The password hash.
    """
    return stauth.Hasher([password]).generate()[0]


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

    # this dataset to all annotators qho are admin
    annotators = db.session.query(Annotator).filter(Annotator.isadmin == True).all()
    for annotator in annotators:
        annotator.datasets.append(dataset)
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
        dataset.annotators = []
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


def get_annotators_of_dataset(id: int) -> List[Annotator]:
    """Get the annotators of a dataset.

    Args:
        id (int): The dataset id.

    Returns:
        List[Annotator]: The list of annotators.
    """
    app_logger.debug(f"POSTGRES: Getting annotators of dataset {id}")
    with db.session.begin():
        # check if the dataset exists
        dataset = db.session.query(Dataset).filter(Dataset.id == id).first()
        if not dataset:
            raise ValueError(f"Dataset {id} does not exist")
        annotators = dataset.annotators
        db.session.commit()
    return annotators


def get_annotations_of_dataset(id: int) -> List[dict]:
    # need to join samples, annotations, annotators. it should return annotation and together with annotater name
    app_logger.debug(f"POSTGRES: Getting annotations of dataset {id}")
    with db.session.begin():
        # check if the dataset exists
        dataset = db.session.query(Dataset).filter(Dataset.id == id).first()
        if not dataset:
            raise ValueError(f"Dataset {id} does not exist")
        # join annotator and annotation and only get annotations of samples of this dataset
        # for each annotation also append the annotator name by joining on annotator_id
        results = (
            session.query(Annotation, Annotator, Sample)
            .join(Sample, Annotation.sample_id == Sample.id)
            .join(Annotator, Annotation.annotator_id == Annotator.id)
            .filter(Sample.dataset_id == id)
        )
        results = results.all()
        # Process the results and create a list of dictionaries
        annotations_list = []
        for annotation, annotator, sample in results:
            annotation_dict = {
                "id": annotation.id,
                "sample_id": annotation.sample_id,
                "annotator_id": annotation.annotator_id,
                "created_at": str(annotation.created_at),
                "final_text": annotation.final_text,
                "isRepated": annotation.isRepated,
                "isAccentRight": annotation.isAccentRight,
                "isClean": annotation.isClean,
                "isSpeedRight": annotation.isSpeedRight,
                "feedback": annotation.feedback,
                "status": annotation.status,
                "final_sentence_type": annotation.final_sentence_type,
                "isPronunciationRight": annotation.isPronunciationRight,
                "isPausesRight": annotation.isPausesRight,
                "isConsisent": annotation.isConsisent,
                "annotator_name": annotator.name,
                "filename": sample.filename,
                "original_text": sample.original_text,
            }
            annotations_list.append(annotation_dict)

    return annotations_list


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


def create_annotator(username: str, name: str, email: str, password: str, ispreauthorized: bool = True, isadmin: bool = False) -> Annotator:
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

        annotator = Annotator(
            username=username, name=name, email=email, hashed_password=generate_password_hash(password), ispreauthorized=ispreauthorized, isadmin=isadmin
        )
        yaml_path = paths.LOGIN_CONFIG_PATH

        if not yaml_path.exists():
            app_logger.info("Creating login config file")
            yaml_path.parent.mkdir(parents=True, exist_ok=True)
            yaml_path.touch()

            config = {
                "credentials": {"usernames": {}},
                "cookie": {"expiry_days": 0, "key": "some_signature_key", "name": "some_cookie_name"},
                "preauthorized": {"emails": []},
            }
            with open(yaml_path, "w") as file:
                yaml.dump(config, file, default_flow_style=False)

        with open(yaml_path) as file:
            config = yaml.load(file, Loader=SafeLoader)

        # add  the annotator to the login config

        config["credentials"]["usernames"][username] = {  # type: ignore
            "email": annotator.email,
            "name": annotator.name,
            "password": annotator.hashed_password,
        }

        if annotator.ispreauthorized:
            if annotator.email not in config["preauthorized"]["emails"]:  # type: ignore
                raise ValueError(f"Annotator {username} is not preauthorized")

        with open(yaml_path, "w") as file:
            yaml.dump(config, file)

        # try to commit the annotator to the database if it fails, delete the annotator from the login config
        try:
            db.session.add(annotator)
            if annotator.isadmin:
                # assign all dataset to the admin
                datasets = db.session.query(Dataset).all()
                for dataset in datasets:
                    annotator.datasets.append(dataset)
                db.session.commit()
        except Exception as e:
            app_logger.error(f"POSTGRES: Failed to create annotator {username}")
            app_logger.error(e)
            # delete the annotator from the login config
            del config["credentials"]["usernames"][username]  # type: ignore
            # if annotator.ispreauthorized:
            #     config["preauthorized"]["emails"].remove(annotator.email)  # type: ignore
            with open(yaml_path, "w") as file:
                yaml.dump(config, file, default_flow_style=False)
            raise e
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
        if annotator.isadmin:
            raise ValueError("Cannot delete admin annotator")
        annotator.datasets = []

        with open(paths.LOGIN_CONFIG_PATH) as file:
            config = yaml.load(file, Loader=SafeLoader)

        config_copy = config.copy()
        # delete the annotator from the login config
        del config["credentials"]["usernames"][annotator.username]
        if annotator.ispreauthorized:
            config["preauthorized"]["emails"].remove(annotator.email)
        with open(paths.LOGIN_CONFIG_PATH, "w") as file:
            yaml.dump(config, file, default_flow_style=False)
        try:
            db.session.query(Annotator).filter(Annotator.id == id).delete()
            db.session.commit()
        except Exception as e:
            app_logger.error(f"POSTGRES: Failed to delete annotator {id}")
            app_logger.error(e)
            # restore the annotator in the login config
            with open(paths.LOGIN_CONFIG_PATH, "w") as file:
                yaml.dump(config_copy, file, default_flow_style=False)
            raise e


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


def get_annotator_by_username(username: str) -> Annotator:
    """Get an annotator by username.

    Args:
        username (str): The annotator username to get.

    Returns:
        Annotator: The annotator.
    """
    app_logger.debug(f"POSTGRES: Getting annotator {username}")
    with db.session.begin():
        # check if the annotator exists
        annotator = db.session.query(Annotator).filter(Annotator.username == username).first()
        if not annotator:
            raise ValueError(f"Annotator {username} does not exist")

        annotator = db.session.query(Annotator).filter(Annotator.username == username).first()
        db.session.commit()
    return annotator


def assign_annotator_to_dataset(annotator_id: int, dataset_id: int) -> None:
    """Assign a dataset to an annotator.

    Args:
        dataset_id (int): The dataset id to assign.
        annotator_id (int): The annotator id to assign.
    """
    app_logger.debug(f"POSTGRES: Assigning dataset {dataset_id} to annotator {annotator_id}")
    with db.session.begin():
        # check if the dataset exists
        dataset = db.session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} does not exist")

        # check if the annotator exists
        annotator = db.session.query(Annotator).filter(Annotator.id == annotator_id).first()
        if not annotator:
            raise ValueError(f"Annotator {annotator_id} does not exist")

        # check if the annotator already has the dataset assigned
        if dataset in annotator.datasets:
            raise ValueError(f"Annotator {annotator_id} already has dataset {dataset_id} assigned")

        annotator.datasets.append(dataset)
        db.session.commit()


def get_datasets_of_annotator(annotator_id: int) -> List[Dataset]:
    """Get the datasets of an annotator.

    Args:
        annotator_id (int): The annotator id to get the datasets from.

    Returns:
        List[Dataset]: The datasets of the annotator.
    """
    app_logger.debug(f"POSTGRES: Getting datasets of annotator {annotator_id}")
    with db.session.begin():
        # check if the annotator exists
        annotator = db.session.query(Annotator).filter(Annotator.id == annotator_id).first()
        if not annotator:
            raise ValueError(f"Annotator {annotator_id} does not exist")

        datasets = annotator.datasets
        db.session.commit()
    return datasets


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
## ANNOTATIONS UTILS ###
########################


def list_annotations() -> List[Annotation]:
    """List all annotations.

    Returns:
        List[Annotation]: The list of annotations.
    """
    app_logger.debug(f"POSTGRES: Listing annotations")
    with db.session.begin():
        annotations = db.session.query(Annotation).all()
        db.session.commit()
    return annotations


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
    isRepeated: bool,
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
            isRepeated=isRepeated,
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


def query_next_sample(dataset_id: int) -> Tuple[List[Sample], dict]:
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

        # join samples and annotations to get the next sample where wer>0.2
        # the difference in  lenght of asr_tex and original text should be more than 5 percent of the original text
        all = (
            db.session.query(Sample, Annotation)
            .outerjoin(Annotation, Sample.id == Annotation.sample_id)
            .filter(Sample.dataset_id == dataset_id)
            .filter(Sample.wer > 0.2)
            .filter(func.length(Sample.asr_text) - func.length(Sample.original_text) > 0.02 * func.length(Sample.original_text))
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

        # number of samples that have been annotated
        annotated = len(all) - len(samples)

        # number of samples that have not been annotated
        not_annotated = len(samples)

    if len(samples) == 0:
        return None, {"annotated": annotated, "not_annotated": not_annotated, "total": annotated + not_annotated}
    return samples[0], {"annotated": annotated, "not_annotated": not_annotated, "total": annotated + not_annotated}


def insert_sample(
    dataset_id: int,
    text: str,
    audio_path: str,
    sentence_type: str,
    sentence_length: int,
    deliverable: str,
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

            if meta["isPCM"] == False:
                convert_to_s16le(local_path, local_path)

            meta = evaluate_audio(local_path)

            sample = Sample(
                dataset_id=dataset_id,
                deliverable=deliverable,
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


from sqlalchemy.orm import Session


def upload_file(session_, row, dataset_id, filename, s3, bucket_name, deliverable):
    # make sure that db is closed

    meta = evaluate_audio(row["local_path"])
    local_path = os.path.join(str(paths.LOCAL_BUCKET_DIR.resolve()), row["s3RawPath"])
    # copy the file to the temp directory
    shutil.copy(row["local_path"], local_path)
    if meta["is_88khz"] == False:
        convert_to_88k(row["local_path"], local_path)

    if meta["peak_volume_db"] < -6 or meta["peak_volume_db"] > -3:
        normalize_audio(local_path, local_path)

    if meta["isPCM"] == False:
        convert_to_s16le(local_path, local_path)

    meta = evaluate_audio(local_path)

    sample = Sample(
        dataset_id=dataset_id,
        deliverable=deliverable,
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

    session_.add(sample)
    s3.upload_file(row["local_path"], bucket_name, row["s3RawPath"])
    session_.commit()


def upload_wav_samples(job: Task, session_: Session, dataset_id: int, csv_path: str, deliverable: str):

    # get dataset
    dataset = session_.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise ValueError(f"Dataset {dataset_id} does not exist")
    dataset = session_.query(Dataset).filter(Dataset.id == dataset_id).first()
    session_.commit()
    dataset_name = dataset.name
    bucket_name = os.environ.get("S3_BUCKET_NAME")
    dataset_dir = os.environ.get("S3_DATASET_DIR")

    print("CSV_PATH: ", csv_path)
    print("My current working directory: ", os.getcwd())
    # Simulate a long-running process
    df = pd.read_csv(csv_path)

    df["s3RawPath"] = df["file_name"].apply(lambda x: os.path.join(dataset_dir, dataset_name, "raw", x))

    s3 = boto3.client("s3", aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"), aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"))

    # Check if the dataset already exists
    dataset = session_.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise ValueError(f"Dataset {dataset_id} does not exist")
    failed: List[str] = []
    # get_metadata of each sample using evaluate_audio method that return dict
    progress = tqdm(total=len(df), desc="Processing")
    for i, row in df.iterrows():
        progress.update(1)
        percentage = int(progress.n / progress.total * 100)
        try:
            filename = os.path.basename(row["local_path"])
            # if there is file in the database with the same name and dataset id then skip it
            sample = session_.query(Sample).filter(Sample.filename == filename).filter(Sample.dataset_id == dataset_id).first()
            if sample:
                app_logger.debug(f"POSTGRES: Sample {filename} already exists in dataset {dataset_id}")
                continue
            # run with thread pool
            with ThreadPoolExecutor(max_workers=10) as executor:
                future = executor.submit(upload_file, session_, row, dataset_id, filename, s3, bucket_name, deliverable)
                future.result()
            if job:
                job.update_state(state="PROGRESS", meta={"progress": percentage, "onboarded_samples": progress.n - len(failed), "failed_samples": failed})
        except Exception as e:
            app_logger.error(f"POSTGRES: Error uploading sample {row['file_name']}: {e}")
            failed.append(row["file_name"])
            if job:
                job.update_state(state="PROGRESS", meta={"progress": percentage, "onboarded_samples": progress.n - len(failed), "failed_samples": failed})
            continue
    progress.close()
    # remove folder that contains csv file
    shutil.rmtree(os.path.dirname(csv_path))
    app_logger.info(f"POSTGRES: Failed to upload {len(failed)} samples: {failed}")
    app_logger.info(f"POSTGRES: Successfully uploaded {len(df) - len(failed)} samples")
    return job
