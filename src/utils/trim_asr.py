import os
import sys
from concurrent.futures import ThreadPoolExecutor
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
from src.utils.audio import asr_and_trim, trim_audio


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


def postprocess(session_, sample, language):
    response = asr_and_trim(sample.s3RawPath, language)
    sample.asr_text = str(response["asr_text"])
    sample.trim_start = round(float(response["trim_start"]), 2)
    sample.trim_end = round(float(response["trim_end"]), 2)
    sample.trimmed_audio_duration = round(float(response["trimmed_audio_duration"]), 2)
    sample.longest_pause = round(float(response["longest_pause"]), 2)
    sample.wer = round(float(utils.calculate_wer(sample.original_text, sample.asr_text)), 2)
    out_path = trim_audio(sample.local_path, sample.trim_start, sample.trim_end, sample.local_path.replace("raw", "trimmed"))
    # update sample
    object_key = out_path.split(f"{str(paths.LOCAL_BUCKET_DIR)}")[1]
    s3TrimmedPath = f"s3://{bucket_name}/{object_key}"

    sample.local_trimmed_path = out_path
    sample.s3TrimmedPath = str(s3TrimmedPath)
    session_.add(sample)
    s3.upload_file(out_path, bucket_name, object_key)


def process_datasets():
    datasets = session.query(Dataset).all()

    for dataset in datasets:
        app_logger.info(f"Processing dataset: {dataset.name}")

        language = dataset.language
        samples = session.query(Sample).filter(Sample.dataset_id == dataset.id).filter(Sample.asr_text == None).all()
        while len(samples) > 0:
            # for sample in tqdm(samples):
            #     # get asr_text
            #     postprocess(session, sample, language)
            # do the above as threads
            with ThreadPoolExecutor(max_workers=10) as executor:
                for sample in samples:
                    executor.submit(postprocess, session, sample, language)
            # # commit changes
            session.commit()
            # get samples with asr_text = null
            samples = session.query(Sample).filter(Sample.dataset_id == dataset.id).filter(Sample.asr_text == None).all()

        app_logger.info(f"Finished processing dataset: {dataset.name}")


if __name__ == "__main__":
    process_datasets()
    app_logger.info("Finished processing all datasets")
