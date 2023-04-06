# This scripts contains the dataset investigate page
# it select datalaset select list and after selecting the dataset it shows the dataset details
# and the samples of the dataset
import os
import sys

import requests
import streamlit as st


current_file_path = os.path.dirname(os.path.abspath(__file__))
# aapedn 3 parent directories to the path
sys.path.append(os.path.join(current_file_path, "..", "..", ".."))

import pandas as pd
from dotenv import load_dotenv

from src.logger import root_logger
from src.paths import paths


BASE_DIR = str(paths.PROJECT_ROOT_DIR.resolve())
# load the .env file
load_dotenv(os.path.join(BASE_DIR, "vars.env"))

lang2idx = {
    "English": "en",
    "German": "de",
    "French": "fr",
    "Spanish": "es",
    "Italian": "it",
}

idx2lang = {v: k for k, v in lang2idx.items()}

app_logger = root_logger.getChild("web_app::create_dataset")
BACKEND_URL = "http://{}:{}".format(os.environ.get("SERVER_HOST"), os.environ.get("SERVER_PORT"))


def app():
    # set wide layout
    # st.set_page_config(layout="wide")

    st.title("TTS Datasets")

    def get_datasets():
        return requests.get(BACKEND_URL + "/datasets").json()

    datasets = get_datasets()
    # either select a dataset or create a new one
    selected_dataset_name = st.selectbox("Dataset", [dataset["name"] for dataset in datasets])
    top_k = st.number_input("Top K", min_value=1, max_value=200, value=10)

    if st.button("Bring Samples") and selected_dataset_name is not None:
        selected_dataset = [dataset for dataset in datasets if dataset["name"] == selected_dataset_name][0]
        selected_dataset_id = selected_dataset["id"]
        samples = requests.get(BACKEND_URL + f"/datasets/{selected_dataset_id}/samples", params={"top_k": top_k}).json()
        df_samples = pd.DataFrame(samples)
        columns = [
            "id",
            "dataset_id",
            "filename",
            "s3url",
            "original_text",
            "asr_text",
            "duration",
            "sentence_type",
            "sentence_length",
            "sampling_rate",
            "sample_format",
            "isPCM",
            "n_channel",
            "format",
            "peak_volume_db",
            "size",
            "isValid",
            "trim_start",
            "trim_end",
            "longest_pause",
            "wer",
        ]
        df_samples = df_samples[columns]

        # # sort on wer such that highest wer is on top
        # df_samples = df_samples.sort_values(by="wer", ascending=False)
        st.write(f"Dataset: {selected_dataset_name}")
        st.table(df_samples)
