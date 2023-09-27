# This scripts contains the dataset investigate page
# it select datalaset select list and after selecting the dataset it shows the dataset details
# and the samples of the dataset
import os
import sys

import plotly.express as px
import plotly.figure_factory as ff  # noqa: F401
import requests
import streamlit as st


current_file_path = os.path.dirname(os.path.abspath(__file__))
# aapedn 3 parent directories to the path
sys.path.append(os.path.join(current_file_path, "..", "..", "..", ".."))

import pandas as pd
from dotenv import load_dotenv

from src.logger import root_logger
from src.paths import paths


BASE_DIR = str(paths.PROJECT_ROOT_DIR.resolve())
# load the .env file
load_dotenv(os.path.join(BASE_DIR, "vars.env"))

app_logger = root_logger.getChild("web_app::create_dataset")
BACKEND_URL = "http://{}:{}".format(os.environ.get("SERVER_HOST"), os.environ.get("SERVER_PORT"))


import matplotlib.pyplot as plt
from wordcloud import WordCloud  # noqa: F401


def get_samples(dataset_id):
    return requests.get(BACKEND_URL + f"/datasets/{dataset_id}/samples").json()


def get_annotations(dataset_id):
    return requests.get(BACKEND_URL + f"/datasets/{dataset_id}/annotations").json()


def get_annotators(dataset_id):
    return requests.get(BACKEND_URL + f"/datasets/{dataset_id}/annotators").json()


def get_feedback(dataset_id):
    return requests.get(BACKEND_URL + f"/datasets/{dataset_id}/feedback").json()


def get_datasets():
    return requests.get(BACKEND_URL + "/datasets").json()


def display_json(data):
    # If the data is a dictionary, display it as a table
    table_data = None
    if isinstance(data, dict):
        # edit keys: replace _ with " " and title, and make values small case
        data = {k.replace("_", " ").title(): v for k, v in data.items()}
        table_data = pd.DataFrame(data.items(), columns=["", ""])
    # If the data is a list, display it as a table
    elif isinstance(data, list):
        table_data = pd.DataFrame(data)

    if table_data is not None:
        num_rows, num_cols = table_data.shape
        # Calculate the desired height and width of the table
        # You can adjust these values as per your requirement
        table_height = (num_rows + 1) * 30  # 30 pixels per row, plus 1 row for header
        table_width = num_cols * 250  # 150 pixels per column (adjust as desired)

        # Generate the CSS styling for the table
        table_style = f"""
            <style>
                .table-container {{
                    margin-bottom: 20px;
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
        st.markdown(table_style, unsafe_allow_html=True)
        st.markdown(f'<div id="tbl_data">{table_data.to_html(index=False, header=False)}</div>', unsafe_allow_html=True)
    else:
        st.write(data)


def app():

    st.title("TTS Datasets")
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

    datasets = get_datasets()
    dataset_names = [dataset["name"] for dataset in datasets]
    selected_dataset = st.selectbox("Select Dataset", dataset_names)

    if selected_dataset:
        selected_dataset = [dataset for dataset in datasets if dataset["name"] == selected_dataset][0]
        samples = pd.DataFrame(get_samples(selected_dataset["id"]))
        annotations = pd.DataFrame(get_annotations(selected_dataset["id"]))
        annotators = pd.DataFrame(get_annotators(selected_dataset["id"]))

        col1, col2 = st.columns((5, 10))
        with col1:
            st.subheader(f"Dataset")
            display_json(selected_dataset)

        with col2:
            st.subheader("Annotators")
            display_json(annotators)

        st.markdown("---")

        # st.subheader("Sample Information")
        # display_json(samples)

        # col1, col2 = st.columns((1, 1))
        # with col1:
        #     st.subheader("Histogram: Sample Duration")
        #     fig = ff.create_distplot([samples["duration"]], ["duration"])
        #     st.plotly_chart(fig)

        if len(annotations) > 0:
            # download anotations
            st.download_button(
                label="Download Annotations",
                data=annotations.to_csv(index=False),
                file_name=f"{selected_dataset['name']}_annotations.csv",
                mime="text/csv",
            )

            st.subheader("Annotation Information")
            st.dataframe(annotations)

            st.subheader("Histogram: Annotation Status")
            fig = px.histogram(annotations, x="status")
            st.plotly_chart(fig)

            st.subheader("Histogram: Annotators")
            fig = px.histogram(annotations, x="annotator")
            st.plotly_chart(fig)

            st.subheader("Annotation Text Comparison")
            comparison_table = annotations[["filename", "original_text", "final_text"]]
            st.dataframe(comparison_table)

            st.subheader("Feedback Analysis")
            # check if there is any feedback
            feedbacks = " ".join(annotations["feedback"].dropna())

            # remove the space from the feedbacks
            feedbacks = feedbacks.replace(" ", "")
            if feedbacks != "":
                wordcloud = WordCloud(background_color="white").generate(feedbacks)
                fig, ax = plt.subplots()
                ax.imshow(wordcloud, interpolation="bilinear")
                ax.axis("off")
                st.pyplot(fig)
            else:
                st.warning("No feedback found for this dataset")
        else:
            st.warning("No annotations found for this dataset")

        # st.subheader("Annotation Trends over Time")
        # annotations["date"] = pd.to_datetime(annotations["date"])
        # fig, ax = plt.subplots()
        # annotations.groupby(annotations["date"].dt.date).size().plot(kind='line', ax=ax)
        # st.pyplot(fig)


app()
