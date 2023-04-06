import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm


sys.path.append(str(Path(__file__).resolve().parents[2]))


from src.logger import root_logger
from src.paths import paths
from src.service.models import Annotation, Annotator, Base, Dataset, Sample  # noqa: F401
from src.utils.audio import asr_and_trim


app_logger = root_logger.getChild("trimmer")

BASE_DIR = paths.PROJECT_ROOT_DIR

load_dotenv(os.path.join(BASE_DIR, "var.env"))


# get engine from url
POSTGRES_URL = f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}/{os.getenv('POSTGRES_DB')}"

engine = create_engine(POSTGRES_URL)
Session = sessionmaker(bind=engine)
session = Session()


def process_datasets():
    datasets = session.query(Dataset).all()

    for dataset in datasets:
        app_logger.info(f"Processing dataset: {dataset.name}")

        language = dataset.language
        samples = session.query(Sample).filter(Sample.dataset_id == dataset.id).filter(Sample.asr_text == None).all()
        while len(samples) > 0:
            for sample in tqdm(samples):
                # get asr_text
                response = asr_and_trim(sample.s3url, language)
                sample.asr_text = response["asr_text"]
                sample.trim_start = response["trim_start"]
                sample.trim_end = response["trim_end"]
                sample.longest_pause = response["longest_pause"]

                # update sample
                session.add(sample)
                session.commit()

            # get samples with asr_text = null
            samples = session.query(Sample).filter(Sample.dataset_id == dataset.id).filter(Sample.asr_text == None).all()

        app_logger.info(f"Finished processing dataset: {dataset.name}")


if __name__ == "__main__":
    # process_datasets()
    app_logger.info("Finished processing all datasets")
