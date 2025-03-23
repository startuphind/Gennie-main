import asyncio
import os
import streamlit as st

from agent.gennie import gennie
from init_setup import ingestor, markdown_parser

from sqlalchemy import text


import re

from todo_manager.db import get_db_connection


def extract_content(input_string):
    # Define the pattern to match the content between the delimiters
    pattern = re.compile(r'# Reply To User:\s*```(.*?)```', re.DOTALL)

    # Search for the pattern in the input string
    match = pattern.search(input_string)

    if match:
        # Extract and return the content between the delimiters
        return match.group(1).strip()
    else:
        # If pattern not found, return the input string
        return input_string


# Default working directory
DEFAULT_WORKING_DIRECTORY = "/Users/rohanverma/PycharmProjects/NoteAI/working"

# Initialize the UI
st.title('Gennie')



# Process the working directory on startup or change
def ingest_documents(directory):
    if os.path.isdir(directory):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ingestor.ingest_directory(directory))
        st.success(f'Ingested all documents in the directory: {directory}')
    else:
        st.error(f'Invalid directory path: {directory}')


# Initialize Streamlit session state
if "history" not in st.session_state:
    st.session_state['history'] = []

if 'is_ingested' not in st.session_state:
    st.session_state['is_ingested'] = True

if "messages" not in st.session_state:
    st.session_state['messages'] = []

if "user_name" not in st.session_state:
    st.session_state['user_name'] = ""

if "working_directory" not in st.session_state:
    st.session_state['working_directory'] = DEFAULT_WORKING_DIRECTORY

if "is_default_dir_ingested" not in st.session_state:
    st.session_state['is_default_dir_ingested'] = False

# Ingest the default working directory automatically on the first run
if not st.session_state['is_default_dir_ingested']:
    ingest_documents(DEFAULT_WORKING_DIRECTORY)
    st.session_state['is_default_dir_ingested'] = True

# Sidebar input for user's name and working directory
st.sidebar.title("User Information")
user_name = st.sidebar.text_input("Your Name", "Git")
st.session_state['user_name'] = user_name

st.sidebar.title("Directory Settings")
working_directory = st.sidebar.text_input("Working Directory", st.session_state['working_directory'])
if st.sidebar.button("Ingest Directory"):
    st.session_state['working_directory'] = working_directory
    ingest_documents(working_directory)

# Sidebar to display the status of indexed files
st.sidebar.title("Indexed Files")


def display_indexed_files():
    conn = get_db_connection()
    try:
        # Execute the query to select paths from the files table
        result = conn.execute(text('SELECT path FROM files'))
        files = result.fetchall()
    finally:
        conn.close()

    # Display each file path in the Streamlit sidebar
    for file_path, in files:
        st.sidebar.write(file_path)


display_indexed_files()

# Refresh the chat UI with previous messages
def refresh_chat_ui():
    """Refresh the chat UI with previous messages."""
    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                st.markdown(extract_content(markdown_parser.parse_markdown(message["content"])), unsafe_allow_html=True)
            else:
                st.markdown(message["content"], unsafe_allow_html=True)


refresh_chat_ui()

# Chat interface
user_query = st.chat_input("Ask me anything...")
if user_query:
    st.session_state["messages"].append({"role": "user", "content": user_query})
    with st.spinner('Working on your query...'):
        response = asyncio.run(gennie(
            user_query=user_query,
            user_name=st.session_state['user_name'],
            history=st.session_state['history'],
            root_directory=st.session_state['working_directory']
        ))
        st.session_state["history"] = response['messages']
        st.session_state["messages"].append({"role": "assistant", "content": response['reply']})
        st.rerun()