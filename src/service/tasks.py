import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from typing import List

import boto3
import pandas as pd
from celery import Celery, Task
from dotenv import load_dotenv
from tqdm import tqdm

from src.logger import root_logger
from src.paths import paths
from src.service.models import Dataset, Sample  # noqa: F401
from src.utils.audio import convert_to_88k, convert_to_s16le, evaluate_audio, normalize_audio  # noqa: F401


BASE_DIR = str(paths.PROJECT_ROOT_DIR.resolve())
# load the .env file
load_dotenv(os.path.join(BASE_DIR, "vars.env"))

app_logger = root_logger.getChild("celery")
s3_bucket_name = os.environ.get("S3_BUCKET_NAME")
s3_dataset_dir = os.environ.get("S3_DATASET_DIR")


# get engine from url
POSTGRES_URL = os.getenv("POSTGRES_URL")


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


engine = create_engine(POSTGRES_URL)
Session = sessionmaker(bind=engine)
session = Session()


# Create the Celery app
app = Celery("TTS-QA")

# Configure the broker and result backend
app.conf.broker_url = "redis://localhost:6379/0"
app.conf.result_backend = "redis://localhost:6379/0"


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


def upload_wav_samples(job: Task, dataset_id: int, csv_path: str, deliverable: str):

    # get dataset
    dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise ValueError(f"Dataset {dataset_id} does not exist")
    dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
    session.commit()
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
    dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
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
            sample = session.query(Sample).filter(Sample.filename == filename).filter(Sample.dataset_id == dataset_id).first()
            if sample:
                app_logger.debug(f"POSTGRES: Sample {filename} already exists in dataset {dataset_id}")
                continue
            # run with thread pool
            with ThreadPoolExecutor(max_workers=10) as executor:
                future = executor.submit(upload_file, session, row, dataset_id, filename, s3, bucket_name, deliverable)
                future.result()
            job.update_state(state="PROGRESS", meta={"progress": percentage, "onboarded_samples": progress.n - len(failed), "failed_samples": failed})
        except Exception as e:
            app_logger.error(f"POSTGRES: Error uploading sample {row['file_name']}: {e}")
            failed.append(row["file_name"])
            job.update_state(state="PROGRESS", meta={"progress": percentage, "onboarded_samples": progress.n - len(failed), "failed_samples": failed})

            continue
    progress.close()
    # remove folder that contains csv file
    shutil.rmtree(os.path.dirname(csv_path))
    app_logger.info(f"POSTGRES: Failed to upload {len(failed)} samples: {failed}")
    app_logger.info(f"POSTGRES: Successfully uploaded {len(df) - len(failed)} samples")
    return job


@app.task(bind=True)
def simulate_onboarding_job(self: Task, dataset_id: int, csv_path: str, deliverable: str = None):
    # Simulate a long-running job
    upload_wav_samples(self, dataset_id, csv_path, deliverable=deliverable)
