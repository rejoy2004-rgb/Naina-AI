import streamlit as st
import os
import re
from dotenv import load_dotenv
from openai import OpenAI
from rag.retrieve import retrieve_context


# CONFIG
load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    st.error("OPENROUTER_API_KEY not found")
    st.stop()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)

st.set_page_config(
    page_title="Naina AI",
    page_icon="👁️",
    layout="centered"
)



# UI Layout
col1, col2 = st.columns([3, 1])
with col1:
    st.title("👁️ Naina AI")
    st.caption("Eye Wellness & Vision Therapy Assistant")
with col2:
    st.write("") # Spacers to push the button down slightly for alignment
    st.write("")
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.assessment_active = False
        st.session_state.assessment_questions = 0
        st.rerun()

st.markdown(
    "Welcome to **Naina AI**, your eye wellness and visual therapy companion. "
    "Ask questions about eye conditions, screen strain, or describe your symptoms "
    "to start a guided wellness assessment."
)

model = "openrouter/free"


# SESSION STATE
if "messages" not in st.session_state:
    st.session_state.messages = []

if "assessment_active" not in st.session_state:
    st.session_state.assessment_active = False

if "assessment_questions" not in st.session_state:
    st.session_state.assessment_questions = 0


# CHAT HISTORY
for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# EMERGENCY DETECTION

EMERGENCY_KEYWORDS = [
    "sudden vision loss",
    "blindness",
    "eye injury",
    "chemical splash",
    "severe eye pain",
    "retinal detachment",
    "flashes of light"
]


def emergency_detected(text):

    text = text.lower()

    return any(
        keyword in text
        for keyword in EMERGENCY_KEYWORDS
    )


# SYMPTOM DETECTION
SYMPTOM_KEYWORDS = [
    "dry eye",
    "dry eyes",
    "itching",
    "burning",
    "red eye",
    "red eyes",
    "blurry",
    "blurred",
    "vision",
    "eye strain",
    "myopia",
    "hyperopia",
    "glaucoma",
    "cataract",
    "astigmatism",
    "pain"
]


def symptom_query(text):

    text = text.lower()

    return any(
        re.search(rf"\b{re.escape(word)}\b", text)
        for word in SYMPTOM_KEYWORDS
    )


# SYSTEM PROMPT
SYSTEM_PROMPT = """
You are Nain-Sukh, an AI-powered Eye Wellness, Vision Care, and Nainocular Platform Assistant.

Your role is to help users understand eye-related symptoms, vision conditions, eye health concerns, general eye-care practices, and answer any questions regarding the Nainocular platform (www.nainocular.com).

IMPORTANT RULES:

1. ONLY answer questions related to:
   - Eye health
   - Vision care
   - Eye diseases
   - Eye symptoms
   - Vision problems
   - Myopia
   - Hyperopia
   - Astigmatism
   - Amblyopia
   - Glaucoma
   - Cataracts
   - Dry Eye Disease
   - Eye strain
   - Contact lenses
   - Binocular vision
   - Vision therapy
   - General eye wellness
   - The Nainocular platform (www.nainocular.com), including its safety, compatibility for children, vision therapy games (how to play them, benefits), eye exercises, and health articles

2. If a user asks a question that is NOT related to eyes, vision, ophthalmology, or the Nainocular platform (www.nainocular.com), respond ONLY with:

"👁️ I am Nain-Sukh, an Eye Wellness, Vision Care, and Nainocular Platform Assistant. Please ask a question related to eye health, vision care, eye conditions, or the Nainocular platform."

3. If a user reports symptoms:
   Ask ONE follow-up question at a time.

4. Gather information about:
   - Duration of symptoms
   - Severity
   - Associated symptoms
   - Screen exposure
   - Existing eye conditions
   - Relevant risk factors

5. Continue asking follow-up questions until sufficient information is collected.

6. Once enough information is available, provide:

## 👁️ Eye Health Summary

## 📋 Possible Causes

## ✅ Recommended Care

## ⚠️ When To Seek Professional Help

## 📌 Disclaimer

7. Never diagnose diseases.

8. Never prescribe medications.

9. Use the provided eye-health knowledge base whenever relevant.

10. Remember previous conversation history to provide context-aware responses.

11. Keep explanations simple, clear, and easy for non-medical users to understand.

12. Always encourage users to consult an eye-care professional for persistent, worsening, or concerning symptoms.
"""

# USER INPUT
prompt = st.chat_input(
    "Ask Naina AI..."
)

if prompt:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    try:

        # EMERGENCY
        if emergency_detected(prompt):

            reply = """
⚠️ **Possible Eye Emergency**

Your symptoms may require urgent medical attention.

Please seek immediate care from an ophthalmologist or emergency department.

This assistant cannot assess emergency conditions.
"""

        else:

            # START ASSESSMENT

            if (
                symptom_query(prompt)
                and not st.session_state.assessment_active
            ):

                st.session_state.assessment_active = True
                st.session_state.assessment_questions = 0

            # BUILD CONTEXT
            recent_user_messages = " ".join(
                [
                    msg["content"]
                    for msg in st.session_state.messages[-10:]
                    if msg["role"] == "user"
                ]
            )

            context = retrieve_context(
                recent_user_messages
            )

            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                }
            ]

            messages.append(
                {
                    "role": "system",
                    "content": f"""
Knowledge Base Context:

{context}
"""
                }
            )

            messages.extend(
                st.session_state.messages
            )

            with st.spinner(
                "Analyzing..."
            ):

                response = (
                    client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.3
                    )
                )

            reply = (
                response
                .choices[0]
                .message
                .content
            )

            # Strip special formatting tokens (e.g. <pad>) that some free models leak
            if reply:
                for token in ["<pad>", "<s>", "</s>", "<unk>"]:
                    reply = reply.replace(token, "")

            # TRACK QUESTIONS
            if "?" in reply:

                st.session_state.assessment_questions += 1

            if (
                "## 👁️ Eye Health Summary"
                in reply
            ):

                st.session_state.assessment_active = False
                st.session_state.assessment_questions = 0


        # DISPLAY RESPONSE
        with st.chat_message(
            "assistant"
        ):
            st.markdown(reply)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": reply
            }
        )

    except Exception as e:

        st.error(
            f"Error: {e}"
        )


# (Sidebar removed)