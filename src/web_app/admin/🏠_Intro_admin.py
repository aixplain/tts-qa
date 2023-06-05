import os
import sys

import streamlit as st
import streamlit_authenticator as stauth


current_file_path = os.path.dirname(os.path.abspath(__file__))
# aapedn 3 parent directories to the path
sys.path.append(os.path.join(current_file_path, "..", "..", "..", ".."))

from dotenv import load_dotenv

from src.logger import root_logger
from src.paths import paths


BASE_DIR = str(paths.PROJECT_ROOT_DIR.resolve())

# load the .env file
load_dotenv(os.path.join(BASE_DIR, "vars.env"))


# set app name and icon
st.set_page_config(page_title="aiXplain's TTS Data App", page_icon="🎙️", layout="wide")

app_logger = root_logger.getChild("web_app::home")
BACKEND_URL = "http://{}:{}".format(os.environ.get("SERVER_HOST"), os.environ.get("SERVER_PORT"))

import requests
import yaml
from yaml.loader import SafeLoader


config_file_path = paths.LOGIN_CONFIG_PATH
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
        choice = st.selectbox("Select an option", ["Create User", "Assign Dataset", "Delete User"])
        if choice == "Create User":
            try:
                with st.form("Register user"):
                    email = st.text_input("Email")
                    username = st.text_input("Username")
                    name = st.text_input("Name")
                    isadmin = st.selectbox("Is admin?", ["False", "True"])
                    password = st.text_input("Password", type="password")
                    repeat_password = st.text_input("Repeat password", type="password")
                    submit_button = st.form_submit_button("Add User")

                if submit_button:
                    if password == repeat_password:
                        # create user
                        params = {"password": password, "name": name, "email": email, "isadmin": isadmin, "ispreauthorized": True}
                        response = requests.post(f"{BACKEND_URL}/annotators/{username}", params=params)
                        if response.status_code == 200:
                            response: str = response.json()  # type: ignore
                            if "message" in response:  # type: ignore
                                st.error(response["message"])  # type: ignore
                            else:
                                st.success("User created successfully")

                        else:
                            st.error("Something went wrong")
                    else:
                        st.error("Passwords do not match")
            except Exception as e:
                st.error(e)
        if choice == "Assign Dataset":
            try:
                all_datasets = requests.get(f"{BACKEND_URL}/datasets").json()
                annotators = requests.get(f"{BACKEND_URL}/annotators").json()
                annotator_selected = st.selectbox("To Annotator", [annotator["username"] for annotator in annotators])
                with st.form("Assign dataset"):
                    annotator_id = [annotator["id"] for annotator in annotators if annotator["username"] == annotator_selected][0]
                    assigned_datasets = requests.get(f"{BACKEND_URL}/annotators/{annotator_id}/datasets").json()
                    not_assigned_datasets = [dataset for dataset in all_datasets if dataset not in assigned_datasets]
                    datasets_selected = st.multiselect("Dataset", [dataset["name"] for dataset in not_assigned_datasets])
                    if len(not_assigned_datasets) == 0:
                        st.warning("No datasets or all datasets are assigned to this annotator")
                    submit_button = st.form_submit_button("Assign Dataset")

                if submit_button:
                    # assign dataset
                    for dataset_selected in datasets_selected:
                        dataset_id = [dataset["id"] for dataset in not_assigned_datasets if dataset["name"] == dataset_selected][0]
                        response = requests.post(f"{BACKEND_URL}/annotators/{annotator_id}/datasets/{dataset_id}")
                        if response.status_code == 200:
                            response = response.json()
                            if response["message"] == "Failed":  # type: ignore
                                st.error(response["error"])  # type: ignore
                            else:
                                st.success(f"Dataset {dataset_selected} assigned to {annotator_selected}")
                        else:
                            st.error("Something went wrong")
            except Exception as e:
                st.error(e)
        if choice == "Delete User":
            try:
                annotators = requests.get(f"{BACKEND_URL}/annotators").json()
                with st.form("Delete user"):
                    annotator_selected = st.selectbox("Annotator", [annotator["username"] for annotator in annotators])
                    submit_button = st.form_submit_button("Delete User")
                if submit_button:
                    # delete user
                    annotator_id = [annotator["id"] for annotator in annotators if annotator["username"] == annotator_selected][0]
                    response = requests.delete(f"{BACKEND_URL}/annotators/{annotator_id}")
                    if response.status_code == 200:
                        response = response.json()
                        if "message" in response and response["message"] != "Failed":  # type: ignore
                            st.error(response["error"])  # type: ignore
                        else:
                            st.success(f"User {annotator_selected} deleted")
                    else:
                        st.error("Something went wrong")
            except Exception as e:
                st.error(f"Error: {e}")

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
