import base64
import io
import os
import sys
import tempfile
import zipfile
from glob import glob

import pandas as pd
import requests
import streamlit as st


current_file_path = os.path.dirname(os.path.abspath(__file__))
# aapedn 3 parent directories to the path
sys.path.append(os.path.join(current_file_path, "..", "..", ".."))

from dotenv import load_dotenv

from src.logger import root_logger
from src.paths import paths


BASE_DIR = str(paths.PROJECT_ROOT_DIR.resolve())
# load the .env file
load_dotenv(os.path.join(BASE_DIR, "vars.env"))

lang_map = {
    "English": "en",
    "German": "de",
    "French": "fr",
    "Spanish": "es",
    "Italian": "it",
}

app_logger = root_logger.getChild("web_app::create_dataset")
BACKEND_URL = "http://{}:{}".format(os.environ.get("SERVER_HOST"), os.environ.get("SERVER_PORT"))

# set wide layout
st.set_page_config(layout="wide")

sample_df = pd.read_csv(os.path.join(BASE_DIR, "src", "web_app", "data", "sample_csv.csv"))
sample_zip_path = os.path.join(BASE_DIR, "src", "web_app", "data", "sample_zip.zip")


def app():
    st.title("TTS Datasets")
    st.write("Create a new TTS dataset or select an existing one")
    if "dataset" not in st.session_state:
        st.session_state["dataset"] = {}

    def get_datasets():
        return requests.get(BACKEND_URL + "/datasets").json()

    datasets = get_datasets()

    # either select a dataset or create a new one
    selected_dataset_name = st.selectbox("Dataset", [dataset["name"] for dataset in datasets] + ["Create New TTS Dataset"])

    if selected_dataset_name == "Create New TTS Dataset":
        dataset_name = st.text_input("Dataset Name")
        dataset_description = st.text_input("Dataset Description")
        dataset_language = st.selectbox("Language of Dataset", ["English", "German", "French", "Spanish", "Italian"])

        if st.button("Create Dataset"):
            # create new dataset object
            params = {
                "language": lang_map[dataset_language],
                "description": dataset_description,
            }
            dataset = requests.post(BACKEND_URL + f"/datasets/{dataset_name}", params=params).json()
            st.success("Dataset created successfully")
            st.session_state["dataset"] = dataset
    else:
        # get selected dataset object
        selected_dataset = [dataset for dataset in datasets if dataset["name"] == selected_dataset_name][0]
        st.session_state["dataset"] = selected_dataset

        # after selctiong or creating a dataset, upload a csv file
        if st.session_state["dataset"] != {}:
            # Add a selectox for deleting, updating dataset
            dataset_options = ["Upload Recordings", "Update Dataset", "Delete Dataset"]
            selected_dataset_option = st.selectbox("Actions", dataset_options)
            if selected_dataset_option == "Delete Dataset":
                if st.button("Delete Dataset"):
                    r = requests.delete(BACKEND_URL + "/datasets/{}".format(st.session_state["dataset"]["id"]))
                    st.session_state["dataset"] = {}
                    st.success("Dataset deleted successfully")

            elif selected_dataset_option == "Update Dataset":
                dataset_name = st.text_input("Dataset Name")
                dataset_description = st.text_input("Dataset Description")
                dataset_language = st.selectbox("Language of Dataset", ["English", "German", "French", "Spanish", "Italian"])

                if st.button("Update Dataset"):
                    r = requests.put(
                        BACKEND_URL + "/datasets/{}".format(st.session_state["dataset"]["id"]),
                        json={"dataset_name": dataset_name, "description": dataset_description, "language": lang_map[dataset_language]},
                    )
                    st.write(r.json())
                    st.session_state["dataset"] = r.json()
            elif selected_dataset_option == "Upload Recordings":

                col1, col2 = st.columns(2)
                with col1:
                    # show a sample csv
                    csv = sample_df.to_csv(index=False)
                    b64 = base64.b64encode(csv.encode()).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="sample.csv">Download example csv file</a>'
                    st.markdown(href, unsafe_allow_html=True)

                    # upload csv file
                    uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])

                with col2:
                    # show a sample zip
                    b64 = base64.b64encode(open(sample_zip_path, "rb").read()).decode()
                    href = f'<a href="data:file/zip;base64,{b64}" download="sample.zip">Download example zip file</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    # upload zip file
                    uploaded_zip_file = st.file_uploader("Upload WAVs as zip", type=["zip"])
                if uploaded_file is not None and uploaded_zip_file is not None:
                    if st.button("Upload"):
                        # read csv file
                        csv = pd.read_csv(uploaded_file)
                        # read and unzip zip file
                        zip_bytes = uploaded_zip_file.read()
                        zip_file = io.BytesIO(zip_bytes)
                        # extract zip file to temp directory
                        tempdir = tempfile.TemporaryDirectory()
                        temp_dir = tempdir.name
                        with zipfile.ZipFile(zip_file, "r") as zip_ref:
                            zip_ref.extractall(temp_dir)
                        # get all wav files in temp directory
                        wav_files = glob(os.path.join(temp_dir, "**", "*.wav"), recursive=True)

                        # create a dataframe with the wav files
                        wav_df = pd.DataFrame(wav_files, columns=["local_path"])
                        # add the filename
                        wav_df["file_name"] = wav_df["local_path"].apply(lambda x: os.path.basename(x))

                        # merge the csv and the wav dataframe
                        df = pd.merge(wav_df, csv, on="file_name", how="left")
                        # check if all files were found
                        not_found_files = df[df["local_path"].isnull()]["file_name"].tolist()

                        if len(not_found_files) > 0:
                            st.write("The following files were not found in the csv file:")
                            st.write(not_found_files)
                        else:
                            # save df to a local dir
                            csv_dir = os.path.join(temp_dir, f"{uploaded_file.name}")
                            df.to_csv(csv_dir, index=False)
                            # preprocess all files and save them to the database
                            st.write("Uploading files to database...")
                            params = {
                                "wavs_path": temp_dir,
                                "csv_path": csv_dir,
                            }

                            response = requests.get(BACKEND_URL + "/datasets/{}/upload_from_csv".format(st.session_state["dataset"]["id"]), params=params)
                            st.write(response.json())


app()
