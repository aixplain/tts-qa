import streamlit as st
from pages.create_dataset import app as create_dataset_app
from pages.dataset_investigate import app as dataset_investigate_app


page_names_to_funcs = {
    "Create Dataset": create_dataset_app,
    "Investigate Dataset": dataset_investigate_app,
}

demo_name = st.sidebar.radio("TTS QA Menu", page_names_to_funcs.keys())
page_names_to_funcs[demo_name]()
