import os
import sys

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


def app():

    st.title("TTS QA")
    if "authentication_status" not in st.session_state:
        # forward to the page where the user can login
        st.warning("Please login first")
        st.stop()
    with st.sidebar:
        if st.session_state["authentication_status"]:
            st.write(f'Welcome *{st.session_state["name"]}*')

    def get_datasets():
        return requests.get(BACKEND_URL + "/datasets").json()

    def get_annotators():
        return requests.get(BACKEND_URL + "/annotators").json()

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

    columns_sizes = (40, 5, 5)

    if "sample" not in st.session_state:
        st.session_state["sample"] = None

    if "test_count" not in st.session_state:
        st.session_state["test_count"] = 0

    if "user_input" not in st.session_state:
        st.session_state["user_input"] = {
            "final_text": "",
            "final_sentence_type": "statement",
            "isAccentRight": False,
            "isPronunciationRight": False,
            "isClean": False,
            "isPausesRight": False,
            "isSpeedRight": False,
            "isConsisent": False,
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
        st.session_state["annotator_id"] = None

    if "dataset_id" not in st.session_state:
        st.session_state["dataset_id"] = None

    if "prev_annotator_id" not in st.session_state:
        st.session_state["prev_annotator_id"] = None

    if "prev_dataset_id" not in st.session_state:
        st.session_state["prev_dataset_id"] = None

    if "datasets" not in st.session_state:
        datasets = get_datasets()
        st.session_state["datasets"] = datasets

    if "annotators" not in st.session_state:
        annotators = get_annotators()
        st.session_state["annotators"] = annotators

    def annotate_sample(
        id: int,
        annotator_id: int,
        final_text: str,
        final_sentence_type: str,
        isAccentRight: bool,
        isPronunciationRight: bool,
        isClean: bool,
        isPausesRight: bool,
        isSpeedRight: bool,
        isConsisent: bool,
        feedback: str,
        status: str = "NotReviewed",
    ):

        data = {
            "annotator_id": annotator_id,
            "final_text": final_text,
            "final_sentence_type": final_sentence_type,
            "isAccentRight": isAccentRight,
            "isPronunciationRight": isPronunciationRight,
            "isClean": isClean,
            "isPausesRight": isPausesRight,
            "isSpeedRight": isSpeedRight,
            "isConsisent": isConsisent,
            "feedback": feedback,
            "status": status,
        }
        response = requests.put(BACKEND_URL + f"/samples/{id}", json=data)
        if response.status_code == 200:
            app_logger.info("Sample annotated")
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
                sample = response.json()
                st.session_state["sample"] = sample
                st.session_state["user_input"] = {
                    "final_text": sample["final_text"],
                    "final_sentence_type": sample["sentence_type"],
                    "isAccentRight": False,
                    "isPronunciationRight": False,
                    "isClean": False,
                    "isPausesRight": False,
                    "isSpeedRight": False,
                    "isConsisent": False,
                    "feedback": "",
                    "status": "NotReviewed",
                }
                st.session_state["query_button"] = False
                app_logger.info("Next sample retrieved")
            else:
                st.error("No more samples to annotate")
                app_logger.error("No more samples to annotate")
        except Exception as e:
            app_logger.error(e)

    def sample_container(sample):
        container = st.container()

        col1, col2, col3, col4 = container.columns(4)
        col1.metric("ID", sample["filename"])
        col2.metric("Sentence Type", f"{sample['sentence_type']}")
        col3.metric("Length", "10")
        col4.metric("WER", sample["wer"])

        container.markdown("---")

        container.markdown("## Listen Audio")
        # audio player
        audio_file = open(st.session_state["sample"]["local_trimmed_path"], "rb")
        container.audio(audio_file, format="audio/wav")

        container.markdown("---")
        # Divide screen into 2 columns
        col1, col2 = container.columns(2)
        col1.subheader("Original Text")
        col2.subheader("ASR")

        # For all systems show all output sentences under each other and system names
        original_text = col1.text_area(
            "Original Text",
            sample["original_text"],
            key=f"original_text",
            label_visibility="hidden",
        )

        asr_text = col2.text_area(
            "ASR",
            sample["asr_text"],
            key=f"asr_text",
            label_visibility="hidden",
        )

        # add vertival radio button for each system
        better = st.radio("Selected Transcription", ["Original", "ASR"], key=f"better_select", index=0, horizontal=True)

        ph = st.empty()
        if better != "":
            st.session_state["user_input"]["final_text"] = ph.text_area(
                "Please post edit the text if needed",
                st.session_state["sample"][f"{better.lower()}_text"],
                key=f"best_sys",
            )
        sentence_type_list = ["Statement", "Question", "Exclamation"]
        defult_idx = sentence_type_list.index(sample["sentence_type"].title())
        sentence_type = st.radio("Sentence Type", sentence_type_list, key=f"sentence_type", index=defult_idx, horizontal=True)
        st.session_state["user_input"]["final_sentence_type"] = sentence_type.lower()

    st.session_state["prev_annotator_id"] = st.session_state["annotator_id"]
    st.session_state["prev_dataset_id"] = st.session_state["dataset_id"]
    annotator_selected = st.sidebar.selectbox("Annotator", [a["username"] for a in st.session_state["annotators"]] + ["Create New"])
    if annotator_selected == "Create New":
        username = st.sidebar.text_input("Username")
        email = st.sidebar.text_input("Email")
        params = {
            "email": email,
        }
        if st.sidebar.button("Create"):
            response = requests.post(BACKEND_URL + f"/annotators/{username}", params=params)
            if response.status_code == 200:
                st.sidebar.success("Annotator created successfully")
                # refresh app
                st.session_state["annotators"] = get_annotators()
                st.experimental_rerun()
            else:
                st.sidebar.error("Annotator creation failed")
    else:
        st.session_state["annotator_id"] = [a["id"] for a in st.session_state["annotators"] if a["username"] == annotator_selected][0]

    st.session_state["dataset_id"] = st.sidebar.selectbox(
        "Dataset ",
        [d["name"] for d in st.session_state["datasets"]],
    )
    st.session_state["dataset_id"] = [d["id"] for d in st.session_state["datasets"] if d["name"] == st.session_state["dataset_id"]][0]

    if st.session_state["prev_annotator_id"] != st.session_state["annotator_id"] or st.session_state["prev_dataset_id"] != st.session_state["dataset_id"]:
        st.session_state["query_button"] = True
        st.session_state["annotate_button"] = False
        st.session_state["isFirstRun"] = True
        st.experimental_rerun()
    # progress_status = st.sidebar.empty()
    # progress_bar = st.sidebar.empty()
    # Infomation on remaining and rated samples count
    stats = None  # TODO: Get stats from server
    # progress_status.write(f"{stats['labeled']} Rated, {stats['unlabeled']} Remaining")
    # my_bar = progress_bar.progress(float(stats["labeled"] / stats["unlabeled"]))
    if st.session_state["dataset_id"] is not None and st.session_state["annotator_id"] is not None:

        if st.session_state["query_button"] and st.session_state["isFirstRun"]:
            st.balloons()
            query()
            st.session_state["isFirstRun"] = False
        elif st.session_state["query_button"]:
            query()
            st.session_state["query_button"] = False
            st.session_state["annotate_button"] = False

        if not st.session_state["isFirstRun"]:
            if "message" not in st.session_state["sample"]:
                # Input sentence
                sample_container(st.session_state["sample"])

                with st.form("my_form"):
                    isAccentRight = st.checkbox("Is the accent right?", value=st.session_state["user_input"]["isAccentRight"])
                    isPronunciationRight = st.checkbox("Is the pronunciation right?", value=st.session_state["user_input"]["isPronunciationRight"])
                    isClean = st.checkbox("Is the recording clean - no background noise?", value=st.session_state["user_input"]["isClean"])
                    isPausesRight = st.checkbox("Is the sound free of any distinct pauses?", value=st.session_state["user_input"]["isPausesRight"])
                    isSpeedRight = st.checkbox("Is the speed of the actor normal?", value=st.session_state["user_input"]["isSpeedRight"])
                    isConsisent = st.checkbox(
                        "Is the actor's voice consistent and similar across all segments?", value=st.session_state["user_input"]["isConsisent"]
                    )
                    feedback = st.text_area("Feedback", value=st.session_state["user_input"]["feedback"])
                    discard = st.checkbox("Discard", value=False)

                    st.session_state["user_input"]["isAccentRight"] = isAccentRight
                    st.session_state["user_input"]["isPronunciationRight"] = isPronunciationRight
                    st.session_state["user_input"]["isClean"] = isClean
                    st.session_state["user_input"]["isPausesRight"] = isPausesRight
                    st.session_state["user_input"]["isSpeedRight"] = isSpeedRight
                    st.session_state["user_input"]["isConsisent"] = isConsisent
                    st.session_state["user_input"]["feedback"] = feedback

                    submitted = st.form_submit_button("Submit")
                    if submitted:
                        if feedback == "" and discard == True:
                            st.error("Please provide feedback when discarding a sample")
                        else:
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
