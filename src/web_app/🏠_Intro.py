import streamlit as st


st.set_page_config(layout="wide")

# make a n intro page that describes the app
# it has 4 pages (tabs)
# 1. create / upload a dataset
# 2. record
# 3. qa
# 4. insights

st.title("aiXplain's TTS Data App")

text = """
This app is used to create and manage datasets for TTS models. It has 4 pages:
1. Create / Upload a dataset
2. Record
3. QA
4. Insights
"""

st.markdown(text)
