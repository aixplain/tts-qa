import pandas as pd
import streamlit as st

# Custom imports
from multipage import MultiPage
from pages import create_dataset


st.set_page_config(layout="wide")


# Create an instance of the app
app = MultiPage()

# Title of the main page
# st.title("Data Centric AI")

# Add all your applications (pages) here
# app.add_page("Create Project", create_project.app)
# app.add_page("Dataset Upload", dataset_upload.app)
# app.add_page("Review", review.app)
app.add_page("Create Dataset", create_dataset.app)
# The main app
app.run()
