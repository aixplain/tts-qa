import warnings


warnings.filterwarnings("ignore")

import os

import pandas as pd
import psycopg2

# read environment variables from vars.env
from dotenv import load_dotenv


load_dotenv("../vars.env")

# connect to postgresql db on localhost, post 5432, using user and password from vars.env

import os

import psycopg2


# Define the database credentials
db_host = os.getenv("POSTGRES_HOST")
db_name = os.getenv("POSTGRES_DB")
db_user = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PWD")

total_hours = 20
include_extras = False

from tqdm import tqdm


for dataset_str in [
    "German(Dorothee)"
]:  # ["English(Melynda)", "French(Dorsaf)"]:  # "Italian(Martina)", "Spanish(Violeta)"]:  # "English(Melynda)", "French(Dorsaf)",
    if "English" in dataset_str:
        dataset = "English"
    elif "Spanish" in dataset_str:
        dataset = "Spanish"
    elif "German" in dataset_str:
        dataset = "German"
    elif "French" in dataset_str:
        dataset = "French"
    elif "Italian" in dataset_str:
        dataset = "Italian"
    print(f"Processing {dataset}...")
    df_wav = pd.read_csv(f"/data/tts-qa/share_{total_hours}h/{dataset}/{dataset}.csv")
    if include_extras:
        df_extras = pd.read_csv(f"/data/tts-qa/share_{total_hours}h/{dataset}/{dataset}-extras.csv")
        df = pd.concat([df_wav, df_extras], axis=0)
    else:
        df = df_wav
    # set all samples is_selected_for_delivery to true by matching filename in the postgres database
    filenames = df.filename.to_list()

    # connect to postgres
    conn = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_password)

    # create cursor
    cur = conn.cursor()

    # update all samples to is_seslected_for_delivery = true
    for filename in tqdm(filenames):
        cur.execute(
            f"""
                    UPDATE sample
                    SET is_selected_for_delivery = true
                    WHERE dataset_id IN (
                        SELECT id
                        FROM dataset
                        WHERE name= '{dataset_str}'
                    )
                    AND filename = '{filename}';
                """
        )

        conn.commit()
