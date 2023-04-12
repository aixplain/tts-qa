import streamlit as st


# make a n intro page that describes the app
# it has 4 pages (tabs)
# 1. create / upload a dataset
# 2. record
# 3. qa
# 4. insights

# set app name and icon
st.set_page_config(page_title="aiXplain's TTS Data App", page_icon="🎙️", layout="wide")


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
