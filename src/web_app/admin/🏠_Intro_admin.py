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

# set app name and icon
st.set_page_config(page_title="aiXplain's TTS Data App", page_icon="🎙️", layout="wide")

app_logger = root_logger.getChild("web_app::home")

import yaml
from yaml.loader import SafeLoader


config_file_path = os.path.join(BASE_DIR, "data", "login_config.yaml")
with open(config_file_path) as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config["credentials"], config["cookie"]["name"], config["cookie"]["key"], config["cookie"]["expiry_days"], config["preauthorized"]
)

# sidebar
with st.sidebar:
    name, authentication_status, username = authenticator.login("Login", "main")
    if st.session_state["authentication_status"]:
        authenticator.logout("Logout", "main")
        st.write(f'Welcome *{st.session_state["name"]}*')
        if st.button("Reset password", key="my_reset"):
            try:
                if authenticator.reset_password(username, "Reset password"):
                    st.success("Password modified successfully")
                    with open(config_file_path, "w") as file:
                        yaml.dump(config, file, default_flow_style=False)
            except Exception as e:
                st.error(e)
        if st.button("Register user", key="my_register"):
            try:
                if authenticator.register_user("Register user", preauthorization=True):
                    st.success("User registered successfully")
                    with open(config_file_path, "w") as file:
                        yaml.dump(config, file, default_flow_style=False)
            except Exception as e:
                st.error(e)
        if st.button("Update user details", key="my_update"):
            try:
                if authenticator.update_user_details(username, "Update user details"):
                    st.success("Entries updated successfully")
                    with open(config_file_path, "w") as file:
                        yaml.dump(config, file, default_flow_style=False)
            except Exception as e:
                st.error(e)

    elif st.session_state["authentication_status"] is False:
        st.error("Username/password is incorrect")
        try:
            username_forgot_pw, email_forgot_password, random_password = authenticator.forgot_password("Forgot password")
            if username_forgot_pw:
                st.success("New password sent securely")
                with open(config_file_path, "w") as file:
                    yaml.dump(config, file, default_flow_style=False)
                # Random password to be transferred to user securely
            else:
                st.error("Username not found")
        except Exception as e:
            st.error(e)
    elif st.session_state["authentication_status"] is None:
        st.warning("Please enter your username and password")


st.title("TTS QA: Admin App")
text = """
## Create and Upload Datasets
Welcome to the Create and Upload Datasets page of the Admin Application! Here, you can create new datasets or
upload existing ones to the system for annotators to work on. To create a new dataset, simply click on the "Create Dataset"
button and fill in the required information such as the dataset name, description, and any relevant tags.
You can also upload a CSV file containing your data directly to the system. Once your dataset is created or uploaded, you can assign it to annotators to start the QA process.

## Insight
Welcome to the Insight page of the Admin Application! Here, you can get valuable insights and statistics about the QA
processes and datasets in the system. You can view the overall status of your datasets, such as the number of annotations completed, in progress,
or pending. You can also view detailed statistics on individual datasets, such as the number of correct and incorrect annotations, the time taken for
each annotation, and any issues encountered during the QA process. Use these insights to improve the quality of your datasets and optimize your QA process.
"""


st.markdown(text)

# make a sidebar
st.sidebar.title("Navigation")
st.sidebar.markdown("### Select a page to get started")
