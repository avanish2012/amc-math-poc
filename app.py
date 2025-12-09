import streamlit as st
import google.generativeai as genai
import pandas as pd

# 1. Page Config
st.set_page_config(page_title="Gemini Math Coach", page_icon="♾️")

# 2. API Key Management (Cloud vs Local)
# This checks if the key is stored in the Cloud Secrets. If not, it asks the user.
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Gemini API Key", type="password")

# 3. Sidebar Setup
with st.sidebar:
    st.header("Teacher Settings")
    default_sheet = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRk-iI5pGXbX-u7vnoxOQWj1_5oaCg3-wbN1DK7VwWjB4tPGFfOQc7B1XgLhXk1A/pub?output=csv" 
    sheet_url = st.text_input("Problem Bank (CSV URL)", value=default_sheet)
    
    if st.button("Reset Session"):
        st.session_state.hint_level = 0
        st.session_state.chat_history = []
        st.rerun()

# 4. Load Data
@st.cache_data
def load_problems(url):
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Error loading Sheet. Ensure it is 'Published to Web' as CSV. Error: {e}")
        return pd.DataFrame()

df = load_problems(sheet_url)

# 5. Initialize State
if "current_problem_index" not in st.session_state:
    st.session_state.current_problem_index = 0
if "hint_level" not in st.session_state:
    st.session_state.hint_level = 0
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if df.empty:
    st.stop()
else:
    # Handle index out of bounds if sheet changes
    if st.session_state.current_problem_index >= len(df):
        st.session_state.current_problem_index = 0
    current_problem = df.iloc[st.session_state.current_problem_index]

# 6. The Brain
def get_gemini_hint(problem_text, chat_history, level):
    if not api_key:
        return "⚠️ Please enter an API Key."
    
    genai.configure(api_key=api_key)
    
    system_instruction = f"""
    You are a Socratic Math Coach for AMC 10.
    GOAL: Help the student solve the problem WITHOUT giving the answer.
    CURRENT STATUS: Student is at Hint Level {level}/3.
    INSTRUCTIONS:
    - Level 1: Ask a clarifying question about a definition.
    - Level 2: Suggest the first step.
    - Level 3: Give a formula or strong clue.
    - NEVER reveal the final answer key.
    - Keep responses short.
    """
    
model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest", system_instruction=system_instruction)
    
    history_for_gemini = []
    for msg in chat_history:
        role = "user" if msg["role"] == "user" else "model"
        history_for_gemini.append({"role": role, "parts": [msg["content"]]})

    try:
        chat = model.start_chat(history=history_for_gemini)
        response = chat.send_message(f"Problem: '{problem_text}'. I am stuck. Give me a Level {level} hint.")
        return response.text
    except Exception as e:
        return f"Error contacting Gemini: {e}"

# 7. UI Layout
st.title("Gemini Math Coach 🇬")
st.progress((st.session_state.current_problem_index + 1) / len(df))

st.markdown(f"### Problem #{st.session_state.current_problem_index + 1}")
st.info(current_problem['problem_text'])

# Chat
for msg in st.session_state.chat_history:
    icon = "🧑‍🎓" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=icon):
        st.write(msg["content"])

# Buttons
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("💡 Get Hint"):
        if st.session_state.hint_level < 3:
            st.session_state.hint_level += 1
            with st.spinner("Thinking..."):
                hint = get_gemini_hint(current_problem['problem_text'], st.session_state.chat_history, st.session_state.hint_level)
            st.session_state.chat_history.append({"role": "user", "content": "I'm stuck."})
            st.session_state.chat_history.append({"role": "assistant", "content": hint})
            st.rerun()
        else:
            st.warning("No more hints available!")

with col2:
    user_ans = st.text_input("Your Answer:", placeholder="e.g. 12")
    if st.button("Submit Answer"):
        if str(user_ans).strip() == str(current_problem['answer']):
            st.success("✅ Correct!")
            st.balloons()
            st.markdown(f"**Explanation:** {current_problem['explanation']}")
            if st.button("Next Problem ➡️"):
                st.session_state.current_problem_index += 1
                st.session_state.hint_level = 0
                st.session_state.chat_history = []
                st.rerun()
        else:
            st.error("❌ Try again.")
