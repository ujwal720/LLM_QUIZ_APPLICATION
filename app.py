import streamlit as st
import requests
import json
import re
from dotenv import load_dotenv
import os
load_dotenv()

API_URL = os.getenv("NGROK_URL", "")

st.set_page_config(page_title="Quiz Application with Document-Based Question Generation and LLM Evaluation", page_icon="📝", layout="centered")
st.title("📝 Quiz Application with Document-Based Question Generation and LLM Evaluation")

# Initialize session state
if "quiz" not in st.session_state:
    st.session_state.quiz = None
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "submitted" not in st.session_state:
    st.session_state.submitted = False

uploaded_file = st.file_uploader("Upload your study material (PDF)", type=["pdf"])

def extract_json(text):
    """
    Cleans and extracts JSON arrays from the model response.
    """
    if not text or not isinstance(text, str):
        return None
    try:
        # Search for a JSON list [ ... ]
        match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        # Strip common markdown markers
        text = re.sub(r'```json|```', '', text).strip()
        return json.loads(text)
    except Exception:
        return None

# Sidebar Utilities
with st.sidebar:
    st.header("🛠️ Controls")
    if st.button("🗑️ Reset Application"):
        st.session_state.quiz = None
        st.session_state.user_answers = {}
        st.session_state.submitted = False
        st.rerun()
    st.info(f"Target URL: {API_URL}")

if uploaded_file and st.button("✨ Generate Quiz"):
    with st.spinner("Mistral is reading and generating questions..."):
        try:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
            response = requests.post(f"{API_URL}/generate-quiz", files=files, timeout=120)
            
            if response.status_code == 200:
                raw_data = response.json()
                quiz_content = raw_data.get("quiz")
                
                if not quiz_content:
                    st.error("Empty response from AI. Try again.")
                elif isinstance(quiz_content, str):
                    parsed_quiz = extract_json(quiz_content)
                    st.session_state.quiz = parsed_quiz if parsed_quiz else quiz_content
                else:
                    st.session_state.quiz = quiz_content
                
                st.session_state.user_answers = {}
                st.session_state.submitted = False
                st.rerun() 
            else:
                st.error(f"Backend Error ({response.status_code}): {response.text}")
        except Exception as e:
            st.error(f"Connection failed: {e}")

# Quiz Display Section
if st.session_state.quiz:
    st.divider()
    
    if isinstance(st.session_state.quiz, list):
        # The Form prevents "flickering" and index errors during selection
        with st.form("quiz_form"):
            st.header("Test Your Knowledge")
            
            for i, q in enumerate(st.session_state.quiz):
                st.subheader(f"Q{i+1}: {q.get('question', 'Question missing')}")
                opts = q.get('options', ["A", "B", "C", "D"])
                
                # Assign radio buttons to session state
                st.session_state.user_answers[i] = st.radio(
                    "Choose the best answer:", 
                    opts, 
                    key=f"radio_q{i}"
                )
                st.write("") # Add spacing

            submit_btn = st.form_submit_button("Submit Final Answers")
            
            if submit_btn:
                st.session_state.submitted = True

        # Process Results
        if st.session_state.submitted:
            st.header("Evaluation Results")
            score = 0
            total = len(st.session_state.quiz)
            
            for i, q in enumerate(st.session_state.quiz):
                user_ans = st.session_state.user_answers.get(i)
                correct_ans = q.get('answer', '')
                
                # Check for exact matches
                if str(user_ans).strip() == str(correct_ans).strip():
                    st.success(f"**Q{i+1}: Correct!** ✅")
                    score += 1
                else:
                    st.error(f"**Q{i+1}: Incorrect.** ❌")
                    st.markdown(f"*Your Answer: {user_ans}*")
                    st.markdown(f"*Correct Answer: {correct_ans}*")
            
            st.metric("Total Score", f"{score}/{total}")
            if score == total:
                st.balloons()
                st.success("Perfect Score! You really know your material.")

    else:
        st.warning("Mistral returned raw text. We couldn't parse it into buttons.")
        st.text_area("Raw AI Output", value=st.session_state.quiz, height=300)

    # Developer view at the bottom
    with st.expander("🔍 Debug: View Backend Data"):
        st.json(st.session_state.quiz)