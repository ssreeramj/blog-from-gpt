import asyncio
import time
import streamlit as st
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from writer_agent import get_final_article

load_dotenv()

st.set_page_config(
    layout="wide",
    page_icon=":material/description:",
    page_title="Blog Generator",
)
st.title("🦜🔗 Blog Generator App")

with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"


def generate_response(chat_url):
    response = asyncio.run(get_final_article(chat_url=chat_url))
    st.info(response)


with st.form("my_form"):
    chat_url = st.text_input(
        label="Enter shared ChatGPT URL:",
        placeholder="https://chatgpt.com/share/1d25bae0-fa33-4445-8276-b009a9bc28e1",
        value="",
    )
    submitted = st.form_submit_button("Submit")
    if not openai_api_key:
        st.warning("Please add your OpenAI API key to continue.")
    
    elif submitted:
        with st.spinner(text="Blog Generation in progress..."):
            generate_response(chat_url)
