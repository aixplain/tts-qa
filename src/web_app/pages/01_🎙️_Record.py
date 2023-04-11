import base64
import os
import sys
from glob import glob

import pandas as pd
import streamlit as st
from audio_recorder_streamlit import audio_recorder

from src.utils.audio import convert_to_mono, normalize_audio


current_file_path = os.path.dirname(os.path.abspath(__file__))
# aapedn 3 parent directories to the path
sys.path.append(os.path.join(current_file_path, "..", "..", ".."))
from src.logger import root_logger
from src.paths import paths


BASE_DIR = str(paths.PROJECT_ROOT_DIR.resolve())
app_logger = root_logger.getChild("web_app::record")

sample_df = pd.read_csv(os.path.join(BASE_DIR, "src", "web_app", "data", "sample_record.csv"))

SAVE_DIR_AUDIO = os.path.join(BASE_DIR, "src", "web_app", "data", "audio")
SAVE_DIR_CSV = os.path.join(BASE_DIR, "src", "web_app", "data", "csv")


def app():
    if not os.path.exists(SAVE_DIR_AUDIO):
        os.makedirs(SAVE_DIR_AUDIO)

    if not os.path.exists(SAVE_DIR_CSV):
        os.makedirs(SAVE_DIR_CSV)

    if "csv" not in st.session_state:
        st.session_state.csv = None

    if "row" not in st.session_state:
        st.session_state.row = None

    if "index" not in st.session_state:
        st.session_state.index = None

    if "csv_name" not in st.session_state:
        st.session_state.csv_name = None

    st.title("Record Audio")
    # show a sample csv
    csv = sample_df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="sample.csv">Download example csv file</a>'
    st.markdown(href, unsafe_allow_html=True)

    # select_a_file or upload a file
    files = glob(os.path.join(SAVE_DIR_CSV, "*.csv"))
    files = [os.path.basename(f) for f in files]
    option = st.selectbox("Select a file or upload a file", files + ["Upload a file"])
    if st.session_state.csv is None:
        if option == "Upload a file":
            # upload csv file
            uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])
            if uploaded_file is not None:
                # Name the file
                st.session_state.csv_name = st.text_input("Name the file", value="recordings_1.csv")
                csv = pd.read_csv(uploaded_file, delimiter=",", usecols=["unique_identifier", "text", "sentence_length", "sentence_type"])
                if "record_status" not in csv.columns:
                    csv["record_status"] = "Not Recorded"
                if st.button("Upload"):
                    st.session_state.csv = csv
                    # check the audio files and update if needed
                    audio_files_ids = [os.path.splitext(os.path.basename(f))[0] for f in glob(os.path.join(SAVE_DIR_AUDIO, "*.wav"))]
                    # the ones in the audio_files shold be marked as recorded
                    st.session_state.csv.loc[st.session_state.csv["unique_identifier"].isin(audio_files_ids), "record_status"] = "Recorded"
                    st.session_state.csv.to_csv(os.path.join(SAVE_DIR_CSV, st.session_state.csv_name), index=False)
        else:
            # select a file
            st.session_state.csv_name = os.path.basename(option)
            st.session_state.csv = pd.read_csv(
                os.path.join(SAVE_DIR_CSV, option), delimiter=",", usecols=["unique_identifier", "text", "sentence_length", "sentence_type", "record_status"]
            )

    # now from the csv file, we go in order and record the audio if it is not recorded
    if st.session_state.csv is not None:
        st.session_state.index = st.session_state.csv[st.session_state.csv["record_status"] == "Not Recorded"].index[0]
        st.session_state.row = st.session_state.csv.loc[st.session_state.index]
        # get first row that is not recorded
        if st.session_state.row["record_status"] == "Not Recorded":
            st.write(f"Recording {st.session_state.row['unique_identifier']}")
            # wrte text very bold and big
            col1, col2 = st.columns(2)
            col1.markdown(f"**{st.session_state.row['text']}**", unsafe_allow_html=True)
            with col2:
                audio_bytes = audio_recorder(
                    pause_threshold=1.0, neutral_color="#303030", recording_color="#de1212", icon_name="microphone", icon_size="3x", sample_rate=88_000
                )

            if audio_bytes:
                st.audio(audio_bytes, format="audio/wav")
                col1, col2, col3 = st.columns(3)

                if col1.button("Save"):
                    st.session_state.csv.at[st.session_state.index, "record_status"] = "Recorded"
                    st.session_state.csv.to_csv(os.path.join(SAVE_DIR_CSV, st.session_state.csv_name), index=False)
                    save_path = os.path.join(SAVE_DIR_AUDIO, st.session_state.row["unique_identifier"] + ".wav")
                    with open(save_path, "wb") as f:
                        f.write(audio_bytes)
                    normalize_audio(save_path, save_path)
                    convert_to_mono(save_path, save_path)
                    st.success("Saved")

                if col2.button("Next"):
                    st.session_state.index = st.session_state.csv[st.session_state.csv["record_status"] == "Not Recorded"].index[0]
                    st.session_state.row = st.session_state.csv.loc[st.session_state.index]


app()
