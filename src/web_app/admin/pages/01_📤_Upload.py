import base64
import io
import os
import re
import shutil
import sys
import tempfile
import zipfile
from glob import glob

import pandas as pd
import requests
import streamlit as st


current_file_path = os.path.dirname(os.path.abspath(__file__))
# aapedn 3 parent directories to the path
sys.path.append(os.path.join(current_file_path, "..", "..", "..", ".."))

from dotenv import load_dotenv

from src.logger import root_logger
from src.paths import paths


BASE_DIR = str(paths.PROJECT_ROOT_DIR.resolve())
# load the .env file
load_dotenv(os.path.join(BASE_DIR, "vars.env"))


def run_regex(wav_files, start_id_regex, end_id_regex):
    failed_files = []
    for wav_file in wav_files:
        start_id = re.findall(start_id_regex, wav_file)
        end_id = re.findall(end_id_regex, wav_file)
        if start_id and end_id:
            start_id = int(start_id[0])
            end_id = int(end_id[0])
        else:
            failed_files.append(wav_file)
    return wav_files, failed_files


lang_map = {
    "English": "en",
    "German": "de",
    "French": "fr", 
    "Spanish": "es",
    "Italian": "it",
}

app_logger = root_logger.getChild("web_app::create_dataset")
BACKEND_URL = "http://{}:{}".format(os.environ.get("SERVER_HOST"), os.environ.get("SERVER_PORT"))


def app():
    if "authentication_status" not in st.session_state:
        # forward to the page where the user can login
        st.warning("Please login first")
        st.stop()
    else:
        user = requests.get(f"{BACKEND_URL}/annotators/username/{st.session_state['username']}").json()
        if not user["isadmin"]:
            st.error("You are not authorized to access this page")
            st.stop()

    with st.sidebar:
        if st.session_state["authentication_status"]:
            st.write(f'Welcome *{st.session_state["name"]}*')

    sample_df = pd.read_csv(os.path.join(BASE_DIR, "src", "web_app", "admin", "data", "sample_csv.csv"))
    sample_zip_path = os.path.join(BASE_DIR, "src", "web_app", "admin", "data", "sample_zip.zip")

    st.title("TTS Datasets")
    st.write("Create a new TTS dataset or select an existing one")
    if "dataset" not in st.session_state:
        st.session_state["dataset"] = {}

    if "failed_files" not in st.session_state:
        st.session_state["failed_files"] = []

    if "job_id" not in st.session_state:
        st.session_state["job_id"] = None

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
            st.experimental_rerun()
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
                deliverable = st.text_input("Deliverable Name")
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
                    # checkif the recordings already segmented and zipped or not using a checkbox
                    segmented = st.checkbox("Check if recordings are already segmented", value=True)

                    if not segmented:
                        # ask for a regex term to define start id and end id
                        st.markdown("Define a regex term to extract start and end id from the file names")
                        col2_1, col2_2 = st.columns(2)
                        start_id_regex = col2_1.text_input("Start ID Regex", value=r"From (\d+) -")
                        end_id_regex = col2_2.text_input("End ID Regex", value=r"- (\d+)")

                        test = st.checkbox("Test Regex")
                        if test:
                            # get an example name for wav file and test the regex
                            example_name = st.text_input("Example File Name", value="From 1 - 10.wav")
                            if st.button("Test"):
                                start_id = re.findall(start_id_regex, example_name)
                                end_id = re.findall(end_id_regex, example_name)
                                if start_id and end_id:
                                    st.success("Regex is valid")
                                    st.write(f"Start ID: {int(start_id[0])} - End ID: {int(end_id[0])}")
                                else:
                                    st.error("Regex is invalid")

                if uploaded_file is not None and uploaded_zip_file is not None:
                    button_col1, button_col2 = st.columns((10, 1))
                    if button_col2.button("Upload"):
                        st.session_state["job_id"] = None

                        st.session_state["failed_files"] = []
                        # read csv file
                        csv = pd.read_csv(uploaded_file, delimiter=",", usecols=["unique_identifier", "text", "sentence_length", "sentence_type"])
                        if csv[csv.isnull().any(axis=1)].shape[0] > 0:
                            st.error("CSV file contains NaN values")
                        else:
                            csv["file_name"] = csv["unique_identifier"].apply(lambda x: x + ".wav" if not x.endswith(".wav") else x)
                            csv["file_name"] = csv["file_name"].apply(lambda x: x.upper().replace(".WAV", ".wav"))
                            # read and unzip zip file
                            zip_bytes = uploaded_zip_file.read()
                            zip_file = io.BytesIO(zip_bytes)
                            # extract zip file to temp directory which will not delete until the program is running
                            temp_dir = tempfile.mkdtemp()
                            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                                zip_ref.extractall(temp_dir)
                            # get all wav files in temp directory
                            # pdb.set_trace()
                            wav_files = glob(os.path.join(temp_dir, "**", "*.wav"), recursive=True)

                            # run regex for detection of start and end id for each wav file and the failed ones will be added to a list
                            if not segmented:
                                wav_files, st.session_state["failed_files"] = run_regex(wav_files, start_id_regex, end_id_regex)
                                if len(st.session_state["failed_files"]) > 0:
                                    st.error("Some files could not be processed")
                                    st.write(st.session_state["failed_files"])

                            # create a folder of the wavs in one directory and rename them to their unique identifier

                            tempdir_aggregated = tempfile.mkdtemp()
                            for wav_file in wav_files:
                                # move the wav file to the temp dir
                                shutil.move(wav_file, tempdir_aggregated)
                            # get all wav files in temp directory
                            wav_files = glob(os.path.join(tempdir_aggregated, "**", "*.wav"), recursive=True)

                            # remove old temp dir
                            shutil.rmtree(temp_dir)

                            temp_dir = tempdir_aggregated

                            # create a dataframe with the wav files
                            wav_df = pd.DataFrame(wav_files, columns=["local_path"])
                            # add the filename
                            wav_df["file_name"] = wav_df["local_path"].apply(lambda x: os.path.basename(x))

                            if segmented:
                                wav_df["file_name"] = wav_df["file_name"].apply(lambda x: x.upper().replace(".WAV", ".wav"))
                                # merge the csv and the wav dataframe
                                df = pd.merge(wav_df, csv, on="file_name", how="left")

                                # check if all files were found
                                not_found_files = df[df["text"].isnull()]["file_name"].tolist()

                                if len(not_found_files) > 0:
                                    st.write("The following files were not found in the csv file:")
                                    st.write(not_found_files)
                                    st.warning(
                                        "Please make sure that the file names in the csv file match the file names in the zip file. Processing of the files will continue with the files that were found."
                                    )
                                df = df.dropna(subset=["text"])
                                # save df to a local dir
                                csv_dir = os.path.join(temp_dir, f"{uploaded_file.name}")
                                df.to_csv(csv_dir, index=False)
                                # preprocess all files and save them to the database
                                st.write("Uploading files to database...")

                                params = {
                                    "wavs_path": temp_dir,
                                    "csv_path": csv_dir,
                                    "deliverable": None if deliverable == "" else deliverable,
                                }
                                response = requests.get(
                                    BACKEND_URL + "/datasets/{}/upload_segmented_async".format(st.session_state["dataset"]["id"]), params=params
                                )
                                if response.status_code == 200:
                                    st.session_state["job_id"] = response.json()["job_id"]
                                    st.success("Files upload triggered successfully")
                                else:
                                    st.error("An error occured while uploading the files")
                                    # remove temp_dir
                                    shutil.rmtree(temp_dir, ignore_errors=True)
                            else:
                                if not len(st.session_state["failed_files"]) > 0:
                                    csv_dir = os.path.join(temp_dir, f"{uploaded_file.name}")
                                    csv.to_csv(csv_dir, index=False)
                                    params = {
                                        "wavs_path": temp_dir,
                                        "csv_path": csv_dir,
                                        "deliverable": None if deliverable == "" else deliverable,
                                        "start_id_regex": start_id_regex,
                                        "end_id_regex": end_id_regex,
                                    }
                                    response = requests.get(
                                        BACKEND_URL + "/datasets/{}/upload_unsegmented_async".format(st.session_state["dataset"]["id"]), params=params
                                    )
                                    if response.status_code == 200:
                                        st.session_state["job_id"] = response.json()["job_id"]
                                        st.success("Files upload triggered successfully")
                                    else:
                                        st.error("An error occured while uploading the files")
                                        # remove temp_dir
                                        shutil.rmtree(temp_dir, ignore_errors=True)
                                else:
                                    st.error("Please fix the errors before uploading the files")
                    # if st.session_state["job_id"] is not None and st.button("Check Status"):
                    #     progress_bar = st.progress(0)
                    #     job_id = st.session_state["job_id"]
                    #     response = requests.get(BACKEND_URL + f"/datasets/upload_segmented_async_status/{job_id}")
                    #     if response.status_code == 200:
                    #         # {"status": job.state, "progress": progress, "onboarded_samples": job.info.get("onboarded_samples", 0), "failed_samples": job.info.get("failed_samples", [])}
                    #         response_json = response.json()
                    #         progress_bar.progress(response_json["progress"])
                    #         st.write(f"Samples onboarding for dataset {st.session_state['dataset']['name']} is {response_json['progress']}% complete")
                    #         st.write("Status: {}".format(response_json["status"]))
                    #         st.write("Onboarded Samples Count: {}".format(response_json["onboarded_samples"]))
                    #         st.write("Failed Samples: {}".format(response_json["failed_samples"]))
                    #     else:
                    #         st.error("An error occured while getting the status of the job")


app()
