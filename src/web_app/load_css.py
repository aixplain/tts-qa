"""
https://discuss.streamlit.io/t/are-you-using-html-in-markdown-tell-us-why/96/25
"""
import streamlit as st


def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
