import openai
import streamlit as st
import os
from dotenv import load_dotenv
import redis
from json_to_pdf import *
import json

load_dotenv()

st.markdown("""
<style>
    *, ::before, ::after {
        box-sizing: inherit;
    }
</style>""", unsafe_allow_html=True)

# redis_host = os.getenv('REDIS_HOST')
# redis_port = os.getenv('REDIS_PORT')
# redis_password = os.getenv('REDIS_PASSWORD')

# r = redis.Redis(
#   host=redis_host,
#   port=redis_port,
#   password=redis_password)

# query_params = st.experimental_get_query_params()
# user_token = query_params.get("user_token", [None])[0]

# r.set('user_id', user_token)

# retrieved_user_id = r.get('user_id')
# print(retrieved_user_id.decode('utf-8'))

allowed_uids = st.secrets["ALLOWED_UIDS"]

# def is_uid_allowed(uid):
#     # allowed_uids_env = os.getenv('ALLOWED_UIDS', '')
#     allowed_uids = allowed_uids_env.split(',')
#     st.write("Allowed UIDs:", allowed_uids)
#     return uid in allowed_uids


def is_uid_allowed(uid):
    allowed_uids = st.secrets["ALLOWED_UIDS"]
    # st.write("Allowed UIDs:", allowed_uids)
    return uid in allowed_uids

SECRET_TOKEN = os.environ.get("SECRET_TOKEN")

user_token = st.experimental_get_query_params().get("user_token", [""])[0]  # Default to an empty string if not found

# st.write("uid in allowed_uids", user_token in allowed_uids)
# st.write("User Token:", user_token)
# st.write("Allowed UIDs:", allowed_uids)


# st.error("Access denied")
# st.stop()
if user_token is not None and is_uid_allowed(user_token):
    st.write("Access granted")
else:
    st.error("Access denied")
    st.stop()


st.title("Chat")

openai.api_key = st.secrets["OPENAI_API_KEY"]

# Check if 'hospital_name' is already in the session state, if not initialize with None
if 'hospital_name' not in st.session_state:
    st.session_state.hospital_name = None

# Ask the user for the hospital name if not already provided
if st.session_state.hospital_name is None:
    hospital_name = st.text_input("Which hospital are you going to?")
    if hospital_name:  # If the user has entered a name
        st.session_state.hospital_name = hospital_name  # Store it in session state
        st.write(f"Hospital name stored: {hospital_name}")  # Optional: Confirm the stored name
    else:
        st.stop()  # Stop execution until the user provides a hospital name
else:
    st.write(f"You are going to: {st.session_state.hospital_name}")  # Display the stored hospital nam


query = '''
Follow as told. Do not output the patient's answer. Act as if you were a doctor and ask “What are your symptoms,” and wait for the patient’s input 1.
Then, summarize input 1 and rephrase it into medical terms and output follow up questions that focus on missing details related to those medical terms, and wait for the patient’s input 2. Based on input 2, output using the following format:

[{"Key symptom 1": "<put details about the extent/severity for this symptom>"},

{"Key symptom 2": "<put details about the extent/severity for this symptom>"},

…

{"Key symptom n": "<put details about the extent/severity for this symptom>"}]
'''

if "chat_ended" not in st.session_state:
    st.session_state["chat_ended"] = False

def handle_correction(correction_text):
# Logic to handle the correction details provided by the user
# This might involve logging the issue, notifying an administrator, or dynamically updating the list.
    if correction_text:
        st.session_state.correction_details = correction_text
        # You can add more logic here, such as sending the correction to an API or saving it somewhere.


# Function to handle the user's response to the "Yes" or "No" question
def handle_yes_no_response():
    if st.session_state.yes_pressed:
        st.write("You pressed Yes.")
        if not st.session_state.get("sent_to_hospital", False):  # Check if not already sent
            
            if st.button("Send to hospital"):
                st.write("You pressed Send.")
                # Update the flag
                st.session_state["sent_to_hospital"] = True
                # Now do the sending logic
            

        if st.session_state.get("sent_to_hospital", False):
            # Show a completed message
            st.write("You pressed Send.")
            st.text("Information sent to the hospital!")
        
        # Add further actions here based on the user pressing "Yes"
    elif st.session_state.no_pressed:
        st.text_input("What's not right with the list? Please provide more details:",
                  key='correction_input',
                  on_change=handle_correction)

def is_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError as e:
        return False
    return True

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-4"

if "messages" not in st.session_state:
    st.session_state.messages = [
        {'role': 'user', 'content': query}
    ]

for message in st.session_state.messages[1:]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])




if not st.session_state.chat_ended:
    if prompt := st.chat_input("What are your symptoms?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            for response in openai.ChatCompletion.create(
                model=st.session_state["openai_model"],
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True,
            ):
                full_response += response.choices[0].delta.get("content", "")
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        
        if is_json(full_response):
            json_response = json.loads(full_response)
            if isinstance(json_response, list):
                st.chat_input(disabled=not input)
                st.session_state.chat_ended = True  # Set the flag to True when the formatted list is outputted

                # Now display the Yes/No buttons
                st.session_state.yes_pressed = st.button("Yes", key="yes_button")
                st.session_state.no_pressed = st.button("No", key="no_button")
                st.markdown("Is this accurate?")

                if st.session_state.yes_pressed or st.session_state.no_pressed:
                    handle_yes_no_response()
else:
    # The chat has ended, display the Yes/No buttons only
    st.session_state.yes_pressed = st.button("Yes", key="yes_button")
    st.session_state.no_pressed = st.button("No", key="no_button")
    
    if st.session_state.yes_pressed or st.session_state.no_pressed:
        handle_yes_no_response()