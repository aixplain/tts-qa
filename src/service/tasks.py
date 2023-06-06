import os

from celery import Celery, Task
from dotenv import load_dotenv

from src.logger import root_logger
from src.paths import paths
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
def simulate_onboarding_job(self: Task, dataset_id: int, csv_path: str, deliverable: str = None):
    # Simulate a long-running job
    upload_wav_samples(self, session, dataset_id, csv_path, deliverable=deliverable)
