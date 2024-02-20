import logging
import traceback


logging.basicConfig(level=logging.DEBUG)
import os

import librosa
from tqdm import tqdm

from src.paths import paths
from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv(paths.PROJECT_ROOT_DIR / "vars.env"), override=True)

import sys
from concurrent.futures import as_completed, ThreadPoolExecutor  # noqa: F401
from pathlib import Path

import boto3
import botocore
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


sys.path.append(str(Path(__file__).resolve().parents[2]))


from src.logger import root_logger
from src.paths import paths
from src.service.models import Annotation, Annotator, Base, Dataset, Sample  # noqa: F401
from src.utils import utils
from src.utils.audio import asr_and_trim_aws, asr_and_trim_azure, asr_aws, trim_audio, trim_only


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


client_config = botocore.config.Config(max_pool_connections=50)
s3 = boto3.client(
    "s3", aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"), aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"), config=client_config
)
bucket_name = os.environ.get("S3_BUCKET_NAME")
dataset_dir = os.environ.get("S3_DATASET_DIR")

offset = 0.2

# from src.utils.whisper_model import WhisperTimestampedASR


# whisper_model = WhisperTimestampedASR(model_size="medium", language="english", device="cuda")

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


def wer_wo_punctuation(reference, hypothesis):
    reference = remove_punctuation(reference)
    hypothesis = remove_punctuation(hypothesis)

    uncased_unpunctuated_wer = float(utils.calculate_wer(reference, hypothesis))
    return uncased_unpunctuated_wer


def asr_and_trim_(session_, sample, language, use="azure"):
    if use == "azure":
        response = asr_and_trim_azure(sample.s3RawPath, language)
    elif use == "aws":
        response = asr_and_trim_aws(sample.s3RawPath, language)

    start = float(response["trim_start"]) - offset
    end = float(response["trim_end"]) + offset
    out_path, start, end = trim_audio(sample.local_path, start, end, sample.local_path.replace("raw", "trimmed"))

    sample.trim_start = round(float(start), 2)
    sample.trim_end = round(float(end), 2)
    sample.trimmed_audio_duration = round(float(end - start), 2)
    sample.longest_pause = round(float(response["longest_pause"]), 2)
    sample.asr_text = str(response["asr_text"])
    sample.wer = round(float(utils.calculate_wer(sample.original_text.lower(), sample.asr_text.lower())), 2)

    # update sample
    object_key = out_path.split(f"{str(paths.LOCAL_BUCKET_DIR)}/")[1]
    s3TrimmedPath = f"s3://{bucket_name}/{object_key}"

    sample.local_trimmed_path = out_path
    sample.s3TrimmedPath = str(s3TrimmedPath)
    session_.add(sample)
    s3.upload_file(out_path, bucket_name, object_key)
    session_.commit()


def trim_only_(session_, sample, language):
    response = trim_only(sample.local_path)

    start = float(response["trim_start"]) - offset
    end = float(response["trim_end"]) + offset
    out_path, start, end = trim_audio(sample.local_path, start, end, sample.local_path.replace("raw", "trimmed"))

    sample.trim_start = round(float(start), 2)
    sample.trim_end = round(float(end), 2)
    sample.trimmed_audio_duration = round(float(end - start), 2)
    sample.longest_pause = round(float(response["longest_pause"]), 2)
    sample.wer = round(float(utils.calculate_wer(sample.original_text.lower(), sample.asr_text.lower())), 2)
    # update sample
    object_key = out_path.split(f"{str(paths.LOCAL_BUCKET_DIR)}/")[1]
    s3TrimmedPath = f"s3://{bucket_name}/{object_key}"

    sample.local_trimmed_path = out_path
    sample.s3TrimmedPath = str(s3TrimmedPath)
    session_.add(sample)
    s3.upload_file(out_path, bucket_name, object_key)
    session_.commit()


def trim_and_asr_(sample, language):
    response = trim_only(sample.local_path)

    start = float(response["trim_start"]) - offset
    end = float(response["trim_end"]) + offset
    out_path, start, end = trim_audio(sample.local_path, start, end, sample.local_path.replace("raw", "trimmed"))

    # update sample
    object_key = out_path.split(f"{str(paths.LOCAL_BUCKET_DIR)}/")[1]
    s3TrimmedPath = f"s3://{bucket_name}/{object_key}"

    sample.local_trimmed_path = out_path
    sample.s3TrimmedPath = str(s3TrimmedPath)

    s3.upload_file(out_path, bucket_name, object_key)

    asr = asr_aws(str(s3TrimmedPath), language)
    sample.asr_text = str(asr)
    sample.trim_start = round(float(start), 2)
    sample.trim_end = round(float(end), 2)
    sample.trimmed_audio_duration = round(float(end - start), 2)
    sample.longest_pause = round(float(response["longest_pause"]), 2)
    sample.wer = round(float(utils.calculate_wer(sample.original_text.lower(), str(asr).lower())), 2)
    sample.uncased_unpunctuated_wer = round(float(wer_wo_punctuation(sample.original_text.lower(), str(asr).lower())), 2)
    return sample


def asr_only_(sample, language):
    asr = asr_aws(sample.s3TrimmedPath, language)
    sample.asr_text = str(asr)
    # get duration
    sample.trimmed_audio_duration = librosa.get_duration(filename=sample.local_trimmed_path)
    sample.wer = round(float(utils.calculate_wer(sample.original_text.lower(), str(asr).lower())), 2)
    sample.uncased_unpunctuated_wer = round(float(wer_wo_punctuation(sample.original_text.lower(), str(asr).lower())), 2)
    return sample


def process_datasets():
    datasets = session.query(Dataset).all()
    for dataset in datasets:
        if "English (Alyssa)" in dataset.name:
            continue
        print(f"Processing dataset: {dataset.name}")
        app_logger.info(f"Processing dataset: {dataset.name}")

        language = dataset.language

        samples = (
            session.query(Sample)
            .filter(Sample.dataset_id == dataset.id)
            .filter(
                (Sample.local_trimmed_path == None)
                | (Sample.local_path == None)
                | (Sample.s3TrimmedPath == None)
                | (Sample.s3RawPath == None)
                | (Sample.asr_text == None)
                | (Sample.trim_start == None)
                | (Sample.trim_end == None)
                | (Sample.trimmed_audio_duration == None)
                | (Sample.trimmed_audio_duration == 0)
                | (Sample.longest_pause == None)
                | (Sample.wer == None)
            )
            .all()
        )
        # if len(samples) > 0:
        #     whisper_model.unload()
        #     whisper_model.load(language=lang_map[language])
        while samples:
            with ThreadPoolExecutor(max_workers=32) as executor:
                futures = [executor.submit(trim_and_asr_, sample, language) for sample in samples]

                # Use tqdm to display the progress of processing finished samples
                for future in tqdm(as_completed(futures), total=len(futures), desc="Processing samples"):
                    try:
                        sample = future.result()
                        # Detach the sample from the main session
                        session.expunge(sample)

                        # Create a new temporary session
                        Session = sessionmaker(bind=engine)
                        tmp_session = Session()

                        # Add the sample to the temporary session and commit the changes
                        tmp_session.add(sample)
                        tmp_session.commit()

                        # Close the temporary session
                        tmp_session.close()
                    except Exception as e:
                        app_logger.error(f"Error processing sample: traceback: {traceback.format_exc()}")

            # get samples with asr_text = null
            samples = (
                session.query(Sample)
                .filter(Sample.dataset_id == dataset.id)
                .filter(
                    (Sample.local_trimmed_path == None)
                    | (Sample.local_path == None)
                    | (Sample.s3TrimmedPath == None)
                    | (Sample.s3RawPath == None)
                    | (Sample.asr_text == None)
                    | (Sample.trim_start == None)
                    | (Sample.trim_end == None)
                    | (Sample.trimmed_audio_duration == None)
                    | (Sample.trimmed_audio_duration == 0)
                    | (Sample.longest_pause == None)
                    | (Sample.wer == None)
                )
                .all()
            )

        app_logger.info(f"Finished processing dataset: {dataset.name}")


if __name__ == "__main__":
    app_logger.info("Starting to process all datasets")
    process_datasets()
    session.close()
    app_logger.info("Finished processing all datasets")
