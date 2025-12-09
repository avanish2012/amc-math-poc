import streamlit as st
import google.generativeai as genai
import pandas as pd
import os

# 1. Page Config
st.set_page_config(page_title="Gemini Math Coach", page_icon="♾️")

# --- SIDEBAR & SETUP ---
with st.sidebar:
    st.header("Teacher Settings")
    
    # Secure API Key Handling
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        api_key = st.text_input("Gemini API Key", type="password")

    # Problem Sheet URL
    default_sheet = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRk-iI5pGXbX-u7vnoxOQWj1_5oaCg3-wbN1DK7VwWjB4tPGFfOQc7B1XgLhXk1A/pub?output=csv" 
    sheet_url = st.text_input("Problem Bank (CSV URL)", value=default_sheet)
    
    # Reset Button
    if st.button("Reset Session"):
        st.session_state.hint_level = 0
        st.session_state.chat_history = []
        st.rerun()

# --- MAIN APP LOGIC ---

# 2. Load Data
@st.cache_data
def load_problems(url):
    try:
        # on_bad_lines='skip' ensures the app doesn't crash on bad rows
        df = pd.read_csv(url, on_bad_lines='skip')
        return df
    except Exception as e:
        st.error(f"Error loading Sheet: {e}")
        return pd.DataFrame()

df = load_problems(sheet_url)

# 3. Initialize Session State
if "current_problem_index" not in st.session_state:
    st.session_state.current_problem_index = 0
if "hint_level" not in st.session_state:
    st.session_state.hint_level = 0
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 4. Select Problem (with safety check)
if df.empty:
    st.warning("No problems found. Check your Google Sheet link.")
    st.stop()
elif st.session_state.current_problem_index >= len(df):
    st.session_state.current_problem_index = 0

current_problem = df.iloc[st.session_state.current_problem_index]

# 5. The AI Brain (Clean Version)
def get_gemini_hint(problem_text, chat_history, level):
    if not api_key:
        return "⚠️ Please enter an API Key in the sidebar."
    
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
    
    # Updated to the model we found in your debug panel
    target_model_name = "gemini-1.5-flash"
    
    try:
        model = genai.GenerativeModel(
            model_name=target_model_name, 
            system_instruction=system_instruction
        )
        
        history_for_gemini = []
        for msg in chat_history:
            role = "user" if msg["role"] == "user" else "model"
            history_for_gemini.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=history_for_gemini)
        response = chat.send_message(f"Problem: '{problem_text}'. I am stuck. Give me a Level {level} hint.")
        return response.text
    except Exception as e:
        # Fixed the syntax error here
        return f"Error contacting Gemini ({target_model_name}): {e}"

# 6. User Interface
st.title("Gemini Math Coach 🇬")
st.progress((st.session_state.current_problem_index + 1) / len(df))

st.markdown(f"### Problem #{st.session_state.current_problem_index + 1}")
st.info(current_problem['problem_text'])

# Chat Display
for msg in st.session_state.chat_history:
    icon = "🧑‍🎓" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=icon):
        st.write(msg["content"])

# Interaction Buttons
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("💡 Get Hint"):
        if st.session_state.hint_level < 3:
            st.session_state.hint_level += 1
            with st.spinner(f"Thinking (Level {st.session_state.hint_level})..."):
                hint = get_gemini_hint(current_problem['problem_text'], st.session_state.chat_history, st.session_state.hint_level)
            st.session_state.chat_history.append({"role": "user", "content": "I'm stuck."})
            st.session_state.chat_history.append({"role": "assistant", "content": hint})
            st.rerun()
        else:
            st.warning("No more hints available!")

with col2:
    user_ans = st.text_input("Your Answer:", placeholder="e.g. 12")
    if st.button("Submit Answer"):
        # Convert both to string to avoid number format mismatches
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
