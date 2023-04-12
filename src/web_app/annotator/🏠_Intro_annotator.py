import streamlit as st


# make a n intro page that describes the app
# it has 4 pages (tabs)
# 1. create / upload a dataset
# 2. record
# 3. qa
# 4. insights

# set app name and icon
st.set_page_config(page_title="aiXplain's TTS Data App", page_icon="🎙️", layout="wide")

st.title("TTS QA: Annotator App")
text = """"
## Record Audio from Uploaded CSV Files Prompt
Welcome to the Record Audio from Uploaded CSV Files Prompt page of the Annotator Application!
Here, you will be prompted to record audio for the uploaded CSV files assigned to you for QA.
Simply click on the "Record" button and start speaking when prompted. You can listen to your
recording and re-record if necessary. Once you are satisfied with your recording, submit it for review.
You can track the status of your submissions on the "Dashboard" page.

## Do the QA for the Recordings Done in a Dataset Uploaded to the System
Welcome to the Do the QA for the Recordings Done in a Dataset Uploaded to the System page of the Annotator Application!
Here, you will be assigned datasets for QA based on your expertise and availability. Simply listen to the audio recordings
and review them for accuracy and completeness. You can mark the recordings as correct, incorrect, or request further review if necessary.
You can also provide comments or feedback to the admin team if you encounter any issues during the QA process. Use your expertise and attention
to detail to ensure the quality of the datasets in the system.
"""


st.markdown(text)

# make a sidebar
st.sidebar.title("Navigation")
st.sidebar.markdown("### Select a page to get started")
