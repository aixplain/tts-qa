import os
import shutil

from celery import Celery, Task
from dotenv import load_dotenv

from src.logger import root_logger
from src.paths import paths
from src.utils.alignment_utils import align_wavs
from src.utils.db_utils import upload_wav_samples


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
SessionObject = sessionmaker(bind=engine)
session = SessionObject()


# Create the Celery app
app = Celery("TTS-QA")

# Configure the broker and result backend
app.conf.broker_url = "redis://localhost:6379/0"
app.conf.result_backend = "redis://localhost:6379/0"


@app.task(bind=True)
def segmented_onboarding_job(self: Task, dataset_id: int, csv_path: str, deliverable: str = None):
    # Simulate a long-running job
    app_logger.info("Starting segmented onboarding job")
    upload_wav_samples(self, session, dataset_id, csv_path, deliverable=deliverable)


@app.task(bind=True)
def unsegmented_onboarding_job(
    self: Task, dataset_id: int, language: str, wavs_path: str, csv_path: str, start_id_regex: str, end_id_regex: str, deliverable: str = None
):

    app_logger.info("Starting unsegmented onboarding job")

    app_logger.info(f"dataset_id: {dataset_id}")
    app_logger.info(f"wavs_path: {wavs_path}")
    app_logger.info(f"csv_path: {csv_path}")
    app_logger.info(f"deliverable: {deliverable}")
    # do alignment first and then upload
    aligned_wavs_dir, aligned_csv_path = align_wavs(self, wavs_path, csv_path, language, start_id_regex, end_id_regex, assigned_only=True)

    # TODO: make sure that you keep the aligned csv
    shutil.rmtree(wavs_path, ignore_errors=True)
    shutil.rmtree(csv_path, ignore_errors=True)

    app_logger.debug(f"aligned_wavs_dir: {aligned_wavs_dir}")

    # Simulate a long-running job
    upload_wav_samples(self, session, dataset_id, aligned_csv_path, deliverable=deliverable)


def unsegmented_onboarding_job_sync(
    dataset_id: int, language: str, wavs_path: str, csv_path: str, start_id_regex: str, end_id_regex: str, deliverable: str = None
):

    app_logger.info("Starting unsegmented onboarding job")

    app_logger.info(f"dataset_id: {dataset_id}")
    app_logger.info(f"wavs_path: {wavs_path}")
    app_logger.info(f"csv_path: {csv_path}")
    app_logger.info(f"deliverable: {deliverable}")
    # do alignment first and then upload
    aligned_wavs_dir, aligned_csv_path = align_wavs(None, wavs_path, csv_path, language, start_id_regex, end_id_regex, assigned_only=True)

    # TODO: make sure that you keep the aligned csv
    shutil.rmtree(wavs_path, ignore_errors=True)
    shutil.rmtree(csv_path, ignore_errors=True)

    app_logger.debug(f"aligned_wavs_dirh: {aligned_wavs_dir}")

    # Simulate a long-running job
    upload_wav_samples(None, session, dataset_id, aligned_csv_path, deliverable=deliverable)
