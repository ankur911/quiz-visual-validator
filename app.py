import os
import json
import pandas as pd
import streamlit as st

# Configuration paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMBINED_DIR = os.path.join(BASE_DIR, "combined_data")
JSON_PATH = os.path.join(COMBINED_DIR, "clean_image_quizzes_4_6.json")
ASSETS_DIR = os.path.join(BASE_DIR, "image_quiz_4_6", "assets")
FEEDBACK_CSV = os.path.join(COMBINED_DIR, "human_validation_feedback.csv")

st.set_page_config(page_title="Quiz Visual Validator & Feedback", layout="wide")

# Custom CSS for styling
st.markdown(
    """
    <style>
    .stImage img {
        border-radius: 50%;
        width: 160px;
        height: 160px;
        object-fit: cover;
        border: 4px solid #ffffff;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    }
    .quiz-card {
        background-color: #1e1e2f;
        padding: 25px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_quizzes():
  if not os.path.exists(JSON_PATH):
    return []
  with open(JSON_PATH, "r", encoding="utf-8") as f:
    return json.load(f)


def load_feedback():
  if os.path.exists(FEEDBACK_CSV):
    return pd.read_csv(FEEDBACK_CSV)
  return pd.DataFrame(columns=["quiz_id", "status", "feedback_text"])


def save_feedback(quiz_id, status, feedback_text):
  df_fb = load_feedback()
  # Remove existing entry for this quiz_id if it exists to avoid duplicates
  df_fb = df_fb[df_fb["quiz_id"] != quiz_id]
  # Append new entry
  new_row = pd.DataFrame(
      [{"quiz_id": quiz_id, "status": status, "feedback_text": feedback_text}]
  )
  df_fb = pd.concat([df_fb, new_row], ignore_index=True)
  os.makedirs(COMBINED_DIR, exist_ok=True)
  df_fb.to_csv(FEEDBACK_CSV, index=False)


quizzes = load_quizzes()
df_feedback = load_feedback()

if not quizzes:
  st.error(f"Could not find quiz data at {JSON_PATH}")
else:
  # Sidebar Navigation & Progress Tracker
  st.sidebar.title("Validation Dashboard")

  # Calculate progress
  reviewed_count = (
      len(df_feedback["quiz_id"].unique()) if not df_feedback.empty else 0
  )
  st.sidebar.metric(
      label="Total Reviewed", value=f"{reviewed_count} / {len(quizzes)}"
  )

  quiz_index = st.sidebar.number_input(
      "Jump to Quiz Index",
      min_value=0,
      max_value=len(quizzes) - 1,
      value=0,
      step=1,
  )

  row = quizzes[quiz_index]
  quiz_id = row.get("quiz_id")
  question = row.get("question")
  correct_key = row.get("correct_answer")

  # Fetch existing feedback if already evaluated
  existing_record = (
      df_feedback[df_feedback["quiz_id"] == quiz_id]
      if not df_feedback.empty
      else pd.DataFrame()
  )
  default_status = (
      existing_record["status"].values[0]
      if not existing_record.empty
      else "good"
  )
  default_text = (
      existing_record["feedback_text"].values[0]
      if not existing_record.empty
      else ""
  )

  # Main Quiz View Container
  st.markdown(
      f"<div class='quiz-card'><h2>Quiz Index: {quiz_index} | ID: `{quiz_id}`</h2>"
      f"<h1 style='color: #ffd700;'>{question}</h1></div>",
      unsafe_allow_html=True,
  )

  st.write(
      f"**Topic:** {row.get('topic')} | **Subtopic:**"
      f" {row.get('subtopic_LLM')} | **Correct Answer:**"
      f" `{row.get(correct_key)}`"
  )
  st.markdown("---")

  # Render 4 circular image options side-by-side
  cols = st.columns(4)
  option_columns = ["option_1", "option_2", "option_3", "option_4"]

  for i, opt_col in enumerate(option_columns):
    opt_val = row.get(opt_col)
    if not opt_val or str(opt_val).strip() == "":
      continue

    safe_opt = "".join(
        c if c.isalnum() or c in ("_", "-") else "_" for c in str(opt_val).strip()
    )
    img_filename = f"{quiz_id}_{opt_col}_{safe_opt}.png"
    img_path = os.path.join(ASSETS_DIR, img_filename)

    with cols[i]:
      st.markdown(f"### {opt_val}")
      if os.path.exists(img_path):
        st.image(img_path)
      else:
        st.warning(f"Image missing:\n{img_filename}")

      if opt_col == correct_key:
        st.success("✓ Correct Option")

  st.markdown("---")

  # Evaluation Form Section
  st.subheader("Human Validation & Feedback")
  with st.form(key=f"eval_form_{quiz_id}"):
    status = st.radio(
        "Select Evaluation Option:",
        options=["good", "text option", "change images", "discard"],
        index=[
            "good",
            "text option",
            "change images",
            "discard",
        ].index(default_status),
        horizontal=True,
    )

    feedback_text = st.text_area(
        "Textual Feedback / Remarks:",
        value=default_text,
        placeholder="Type any notes, e.g., 'Image option 2 looks weird' or 'Should be text based'",
    )

    submit_button = st.form_submit_button(
        label="Save Evaluation & Next ➡️"
    )

    if submit_button:
      save_feedback(quiz_id, status, feedback_text)
      st.success(
          f"Feedback saved successfully for quiz {quiz_id}! Data logged to"
          " CSV."
      )