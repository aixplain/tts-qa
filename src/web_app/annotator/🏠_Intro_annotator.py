import os
import sys

import streamlit as st
import streamlit_authenticator as stauth


current_file_path = os.path.dirname(os.path.abspath(__file__))
# aapedn 3 parent directories to the path
sys.path.append(os.path.join(current_file_path, "..", "..", "..", ".."))

from src.logger import root_logger
from src.paths import paths


BASE_DIR = str(paths.PROJECT_ROOT_DIR.resolve())

app_logger = root_logger.getChild("web_app::home")

import yaml
from yaml.loader import SafeLoader


config_file_path = paths.LOGIN_CONFIG_PATH
with open(config_file_path) as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config["credentials"], config["cookie"]["name"], config["cookie"]["key"], config["cookie"]["expiry_days"], config["preauthorized"]
)

# sidebar

name, authentication_status, username = authenticator.login("Login", "sidebar")
if st.session_state["authentication_status"]:
    authenticator.logout("Logout", "sidebar")
    st.sidebar.write(f'Welcome *{st.session_state["name"]}*')

elif st.session_state["authentication_status"] is False:
    st.sidebar.error("Username/password is incorrect")
    try:
        username_forgot_pw, email_forgot_password, random_password = authenticator.forgot_password("Forgot password", "sidebar")
        if username_forgot_pw:
            st.sidebar.success("New password sent securely")
            with open(config_file_path, "w") as file:
                yaml.dump(config, file, default_flow_style=False)
            # Random password to be transferred to user securely
        else:
            st.sidebar.error("Username not found")
    except Exception as e:
        st.error(e)
elif st.session_state["authentication_status"] is None:
    st.sidebar.warning("Please enter your username and password")

st.title("TTS QA: Annotator App")
text = """
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
