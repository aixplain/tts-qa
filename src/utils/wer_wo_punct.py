import os


os.environ["TEAM_API_KEY"] = "2b3632015768088470d98273667a627e0e5a7d2d659ec3cf4b06bfa368eaa1a8"

import sys
from concurrent.futures import ThreadPoolExecutor  # noqa: F401
from pathlib import Path

import boto3
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


sys.path.append(str(Path(__file__).resolve().parents[2]))


from src.logger import root_logger
from src.paths import paths
from src.service.models import Annotation, Annotator, Base, Dataset, Sample  # noqa: F401
from src.utils import utils
from src.utils.audio import asr_and_trim_aws, asr_and_trim_azure, trim_audio, trim_only  # noqa: F401


app_logger = root_logger.getChild("trimmer")

BASE_DIR = paths.PROJECT_ROOT_DIR


if load_dotenv(os.path.join(BASE_DIR, "vars.env")):
    app_logger.info("Loaded env vars from vars.env")
else:
    app_logger.error("Failed to load env vars from vars.env")
    exit(1)


# get engine from url
POSTGRES_URL = os.getenv("POSTGRES_URL")

engine = create_engine(POSTGRES_URL)
Session = sessionmaker(bind=engine)
session = Session()

s3 = boto3.client("s3", aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"), aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"))
bucket_name = os.environ.get("S3_BUCKET_NAME")
dataset_dir = os.environ.get("S3_DATASET_DIR")

offset = 0.2

lang_map = {
    "en": "english",
    "fr": "french",
    "es": "spanish",
    "de": "german",
    "it": "italian",
}


import string


def remove_punctuation(input_string):
    # Make a translator object to remove all punctuation
    translator = str.maketrans("", "", string.punctuation)
    return input_string.translate(translator)


def wer_wo_punctuation(session_, sample):
    reference = remove_punctuation(sample.original_text.lower())
    hypothesis = remove_punctuation(sample.asr_text.lower())

    sample.uncased_unpunctuated_wer = round(float(utils.calculate_wer(reference, hypothesis)), 2)
    session_.add(sample)
    session_.commit()


def process_datasets():
    datasets = session.query(Dataset).all()

    for dataset in datasets:

        print(f"Processing dataset: {dataset.name}")
        app_logger.info(f"Processing dataset: {dataset.name}")

        samples = session.query(Sample).filter(Sample.dataset_id == dataset.id).filter(Sample.uncased_unpunctuated_wer == None).all()

        while samples:  # Continue while there are samples left
            with ThreadPoolExecutor(max_workers=8) as executor:
                # Remove sample from list and process
                while samples:
                    sample = samples.pop(0)
                    executor.submit(wer_wo_punctuation, session, sample)

        app_logger.info(f"Finished processing dataset: {dataset.name}")


if __name__ == "__main__":
    process_datasets()
    app_logger.info("Finished processing all datasets")
