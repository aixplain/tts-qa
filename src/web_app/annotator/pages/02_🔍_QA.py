import os
import sys

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

lang2idx = {
    "English": "en",
    "German": "de",
    "French": "fr",
    "Spanish": "es",
    "Italian": "it",
}

idx2lang = {v: k for k, v in lang2idx.items()}

app_logger = root_logger.getChild("web_app::annotate")
BACKEND_URL = "http://{}:{}".format(os.environ.get("SERVER_HOST"), os.environ.get("SERVER_PORT"))


# Function to display json data in a structured way
def display_json(data, col):
    # If the data is a dictionary, display it as a table
    table_data = None
    if isinstance(data, dict):
        # edit keys: replace _ with " " and title, and make values small case
        # data = {k.replace("_", " ").title(): v for k, v in data.items()}
        table_data = pd.DataFrame(data.items(), columns=["", ""])
    # If the data is a list, display it as a table
    elif isinstance(data, list):
        table_data = pd.DataFrame(data)

    if table_data is not None:
        # transpose the table data
        table_data = table_data.T
        num_rows, num_cols = table_data.shape
        # Calculate the desired height and width of the table
        # You can adjust these values as per your requirement
        table_height = (num_rows + 1) * 50  # 30 pixels per row, plus 1 row for header
        table_width = num_cols * 450  # 150 pixels per column (adjust as desired)

        # Generate the CSS styling for the table
        table_style = f"""
            <style>
                .table-container {{
                    margin-bottom: 50px;
                }}
                .table-container table {{
                    width: {table_width}px;
                    height: {table_height}px;
                    table-layout: fixed;
                }}
                .table-container table tbody {{
                    display: block;
                    height: inherit;
                    overflow: auto;
                }}
                .table-container table thead,
                .table-container table tbody tr {{
                    display: table;
                    width: 100%;
                    table-layout: fixed;
                }}
            </style>
        """
        # Display the table using Streamlit
        col.markdown(table_style, unsafe_allow_html=True)
        col.markdown(f'<div id="tbl_data">{table_data.to_html(index=False, header=False)}</div>', unsafe_allow_html=True)
    else:
        col.write(data)


def app():

    st.title("TTS QA")
    if "authentication_status" not in st.session_state:
        # forward to the page where the user can login
        st.warning("Please login first")
        st.stop()
    with st.sidebar:
        if st.session_state["authentication_status"]:
            st.write(f'Welcome *{st.session_state["name"]}*')

    def get_datasets(annotator_id: int):
        return requests.get(BACKEND_URL + f"/annotators/{annotator_id}/datasets").json()

    st.markdown(
        """
            <style>
            [class^="st-b"]  {
                color: white;
                font-family: monospace;
            }
            footer {
                font-family: monospace;
            }
            .reportview-container .main footer, .reportview-container .main footer a {
                color: #0c0080;
            }
            header .decoration {
                background-image: none;
            }

            </style>
            """,
        unsafe_allow_html=True,
    )

    if "sample" not in st.session_state:
        st.session_state["sample"] = None

    if "run_id" not in st.session_state:
        st.session_state["run_id"] = 0

    if "test_count" not in st.session_state:
        st.session_state["test_count"] = 0

    if "user_input" not in st.session_state:
        st.session_state["user_input"] = {
            "final_text": "",
            "final_sentence_type": "statement",
            "isRepeated": False,
            # "isAccentRight": False,
            # "isPronunciationRight": False,
            # "isClean": False,
            # "isPausesRight": False,
            # "isSpeedRight": False,
            # "isConsisent": False,
            "incorrectProsody": True,
            "inconsistentTextAudio": True,
            "incorrectTrancuation": True,
            "soundArtifacts": True,
            "feedback": "",
            "status": "NotReviewed",
        }

    if "query_button" not in st.session_state:
        st.session_state["query_button"] = True

    if "annotate_button" not in st.session_state:
        st.session_state["annotate_button"] = False

    if "isFirstRun" not in st.session_state:
        st.session_state["isFirstRun"] = True

    if "annotator_id" not in st.session_state:
        annotator = requests.get(BACKEND_URL + f"/annotators/username/{st.session_state['username']}").json()
        st.session_state["annotator_id"] = annotator["id"]

    if "dataset_id" not in st.session_state:
        st.session_state["dataset_id"] = None

    if "prev_dataset_id" not in st.session_state:
        st.session_state["prev_dataset_id"] = None

    if "datasets" not in st.session_state:
        datasets = get_datasets(st.session_state["annotator_id"])
        st.session_state["datasets"] = datasets

    if "stats" not in st.session_state:
        st.session_state["stats"] = {
            "total": 0,
            "annotated": 0,
            "not_annotated": 0,
        }

    def annotate_sample(
        id: int,
        annotator_id: int,
        final_text: str,
        final_sentence_type: str,
        isRepeated: bool,
        # isAccentRight: bool,
        # isPronunciationRight: bool,
        # isClean: bool,
        # isPausesRight: bool,
        # isSpeedRight: bool,
        # isConsisent: bool,
        incorrectProsody: bool,
        inconsistentTextAudio: bool,
        incorrectTrancuation: bool,
        soundArtifacts: bool,
        feedback: str,
        status: str = "NotReviewed",
    ):

        data = {
            "annotator_id": annotator_id,
            "final_text": final_text,
            "final_sentence_type": final_sentence_type,
            "isRepeated": isRepeated,
            # "isAccentRight": isAccentRight,
            # "isPronunciationRight": isPronunciationRight,
            # "isClean": isClean,
            # "isPausesRight": isPausesRight,
            # "isSpeedRight": isSpeedRight,
            # "isConsisent": isConsisent,
            "incorrectProsody": incorrectProsody,
            "inconsistentTextAudio": inconsistentTextAudio,
            "incorrectTrancuation": incorrectTrancuation,
            "soundArtifacts": soundArtifacts,
            "feedback": feedback,
            "status": status,
        }
        response = requests.put(BACKEND_URL + f"/samples/{id}", json=data)
        if response.status_code == 200:
            app_logger.info(f"Sample {id} annotated")
            st.success("Sample annotated")
            # unlock the sample
            response = requests.put(BACKEND_URL + f"/samples/{id}/unlock")
            if response.status_code == 200:
                app_logger.info(f"Sample {id} unlocked")
        else:
            app_logger.error("Sample annotation failed")
            st.error("Sample annotation failed")
        return response

    def query():
        if st.session_state["annotate_button"]:
            if st.session_state["user_input"]["status"] in ["Discarded", "Reviewed"]:
                st.session_state["user_input"].update({"id": st.session_state["sample"]["id"], "annotator_id": st.session_state["annotator_id"]})
                response = annotate_sample(**st.session_state["user_input"])
            st.session_state["annotate_button"] = False

        try:
            # send a request to get next sample
            response = requests.get(BACKEND_URL + f"/datasets/{st.session_state['dataset_id']}/next_sample")
            if response.status_code == 200:
                response = response.json()
                if "message" in response:
                    st.session_state["sample"] = None
                    st.session_state["stats"] = None
                    st.error(f"Error: {response['message']}")
                    app_logger.error("No more samples to annotate")
                    return
                sample = response["sample"]
                stats = response["stats"]
                st.session_state["sample"] = sample
                st.session_state["stats"] = stats
                st.session_state["user_input"] = {
                    "final_text": sample["original_text"],
                    "final_sentence_type": sample["sentence_type"],
                    "isRepeated": False,
                    # "isAccentRight": False,
                    # "isPronunciationRight": False,
                    # "isClean": False,
                    # "isPausesRight": False,
                    # "isSpeedRight": False,
                    # "isConsisent": False,
                    "incorrectProsody": True,
                    "inconsistentTextAudio": True,
                    "incorrectTrancuation": True,
                    "soundArtifacts": True,
                    "feedback": "",
                    "status": "NotReviewed",
                }

                # lock the sample

                response = requests.put(BACKEND_URL + f"/samples/{sample['id']}/lock")
                if response.status_code == 200:
                    app_logger.info(f"Sample {sample['id']} locked")
                st.session_state["query_button"] = False
                app_logger.info("Next sample retrieved")
            else:
                st.error(f"Failed to get next sample, status code: {response.status_code}")
                app_logger.error(f"Failed to get next sample, status code: {response.status_code}")
        except Exception as e:
            app_logger.error(e)

    columns_sizes = (15, 15, 5)

    st.session_state["prev_dataset_id"] = st.session_state["dataset_id"]

    st.session_state["dataset_id"] = st.sidebar.selectbox(
        "Dataset ",
        [d["name"] for d in st.session_state["datasets"]],
    )
    st.session_state["dataset_id"] = [d["id"] for d in st.session_state["datasets"] if d["name"] == st.session_state["dataset_id"]][0]

    if st.session_state["prev_dataset_id"] != st.session_state["dataset_id"]:
        st.session_state["query_button"] = True
        st.session_state["annotate_button"] = False
        st.session_state["isFirstRun"] = True
        if st.session_state["sample"] is not None:
            response = requests.put(BACKEND_URL + f"/samples/{int(st.session_state['sample']['id'])}/unlock")
            if response.status_code == 200:
                app_logger.info(f"Sample {int(st.session_state['sample']['id'])} unlocked")
        st.experimental_rerun()

    if st.session_state["dataset_id"] is not None:

        if st.session_state["query_button"] and st.session_state["isFirstRun"]:
            st.balloons()
            query()
            st.session_state["isFirstRun"] = False
        elif st.session_state["query_button"]:
            query()
            st.session_state["query_button"] = False
            st.session_state["annotate_button"] = False
        # add progresss bar
        if st.session_state["stats"] is not None:
            progress_bar = st.progress(0, text="Progress")
            progress = st.session_state["stats"]["annotated"] / st.session_state["stats"]["total"]
            progress_bar.progress(
                progress,
                text=f"Progress: {st.session_state['stats']['annotated']} Rated, {st.session_state['stats']['total'] - st.session_state['stats']['annotated']} Remaining out of {st.session_state['stats']['total']} recordings",
            )

        if st.session_state["sample"] is not None:

            # Input sentence
            # sample_container(st.session_state["sample"])
            sample = st.session_state["sample"]
            col1, col2, col3, col4 = st.columns(columns_sizes)
            col1.metric("ID", sample["filename"])
            col2.metric("Sentence Type", f"{sample['sentence_type']}")
            col3.metric("WER", sample["wer"])

            st.markdown("### Audio")
            col1, col2 = st.columns((20, 2))
            # audio player
            audio_file = open(st.session_state["sample"]["local_trimmed_path"], "rb")
            col1.audio(audio_file, format="audio/wav")
            submitted1 = col2.button("Submit", key=f"submit_container_{st.session_state['run_id']}")

            # st.markdown("---")
            col1, col2 = st.columns(2)
            original_text = col1.text_area(
                "Original Text",
                f'{sample["original_text"]}',
            )
            asr_text = col2.text_area(
                "ASR Text",
                sample["asr_text"],
            )

            st.markdown("---")

            postedit_columns_sizes = (10, 35, 10, 10)
            # Divide screen into 2 columns
            col2, col3, col4, col5 = st.columns(postedit_columns_sizes)
            # For all systems show all output sentences under each other and system names

            # add vertival radio button for each system
            col2.markdown("### Select Better")
            better = col2.radio(
                "Selected Transcription",
                ["Original", "ASR"],
                key=f"better_select_{st.session_state['run_id']}",
                index=0,
                horizontal=True,
                label_visibility="collapsed",
            )

            col3.markdown("### Post Edit")
            ph = col3.empty()
            if better != "":
                st.session_state["user_input"]["final_text"] = ph.text_area(
                    "Please post edit the text if needed",
                    st.session_state["sample"][f"{better.lower()}_text"],
                    key=f"best_sys_{st.session_state['run_id']}",
                    label_visibility="collapsed",
                )
            col4.markdown("### Sentence Type")
            sentence_type_list = ["Statement", "Question", "Exclamation"]
            defult_idx = sentence_type_list.index(sample["sentence_type"].title())
            sentence_type = col4.radio(
                "Sentence Type", sentence_type_list, key=f"sentence_type_{st.session_state['run_id']}", index=defult_idx, label_visibility="collapsed"
            )
            st.session_state["user_input"]["final_sentence_type"] = sentence_type.lower()

            col5.markdown("#")
            col5.markdown("#")
            col5.markdown("#")
            col5.markdown("###")

            # create a divider
            st.markdown("---")
            # ask if you want to Discard or Save
            col1, col2 = st.columns(2)
            with col1:
                discard = st.checkbox("Discard", value=False, key=f"discard_{st.session_state['run_id']}")

            if discard:
                col1, col2 = st.columns(2)
                with col1:
                    isRepeated = True if st.checkbox("Has Repeation", value=False) else False
                    # isAccentRight = True if st.checkbox("Accent is Wrong", value=False) else False
                    # isPronunciationRight = True if st.checkbox("Pronunciation is Wrong", value=False) else False
                    # isClean = True if st.checkbox("Recording is not Clean", value=False) else False
                    # isPausesRight = True if st.checkbox("Pauses are not right", value=False) else False
                    # isSpeedRight = True if st.checkbox("Speed is not right", value=False) else False
                    # isConsisent = True if st.checkbox("Voice is not consistent", value=False) else False
                    incorrectProsody = True if st.checkbox("Incorrect prosody", value=False) else False
                    inconsistentTextAudio = True if st.checkbox("Inconsistent text and audio", value=False) else False
                    incorrectTrancuation = True if st.checkbox("Incorrect trancuation", value=False) else False
                    soundArtifacts = True if st.checkbox("Sound artifacts", value=False) else False
                with col2:
                    feedback = st.text_area("Feedback", value=st.session_state["user_input"]["feedback"])

                st.session_state["user_input"]["isRepeated"] = isRepeated
                # st.session_state["user_input"]["isAccentRight"] = isAccentRight
                # st.session_state["user_input"]["isPronunciationRight"] = isPronunciationRight
                # st.session_state["user_input"]["isClean"] = isClean
                # st.session_state["user_input"]["isPausesRight"] = isPausesRight
                # st.session_state["user_input"]["isSpeedRight"] = isSpeedRight
                # st.session_state["user_input"]["isConsisent"] = isConsisent
                st.session_state["user_input"]["incorrectProsody"] = incorrectProsody
                st.session_state["user_input"]["inconsistentTextAudio"] = inconsistentTextAudio
                st.session_state["user_input"]["incorrectTrancuation"] = incorrectTrancuation
                st.session_state["user_input"]["soundArtifacts"] = soundArtifacts
                st.session_state["user_input"]["feedback"] = feedback
            else:
                st.session_state["user_input"]["isRepeated"] = True
                # st.session_state["user_input"]["isAccentRight"] = True
                # st.session_state["user_input"]["isPronunciationRight"] = True
                # st.session_state["user_input"]["isClean"] = True
                # st.session_state["user_input"]["isPausesRight"] = True
                # st.session_state["user_input"]["isSpeedRight"] = True
                # st.session_state["user_input"]["isConsisent"] = True
                st.session_state["user_input"]["incorrectProsody"] = False
                st.session_state["user_input"]["inconsistentTextAudio"] = False
                st.session_state["user_input"]["incorrectTrancuation"] = False
                st.session_state["user_input"]["soundArtifacts"] = False
                st.session_state["user_input"]["feedback"] = ""
            col1, col2 = st.columns((10, 1))
            with col2:
                submitted2 = st.button("Submit", key=f"submit_st_{st.session_state['run_id']}")
                if submitted1 or submitted2:
                    st.session_state["run_id"] += 1
                    if discard:
                        status = "Discarded"
                    else:
                        status = "Reviewed"
                    st.session_state["user_input"]["status"] = status
                    st.success("Submitted!")
                    st.session_state["query_button"] = True
                    st.session_state["annotate_button"] = True
                    st.experimental_rerun()

        else:
            st.warning("No more samples to rate")

    else:
        st.warning("Select Annotator and Dataset")


app()
