import streamlit as st
import os
import re
from dotenv import load_dotenv
from openai import OpenAI
from rag.retrieve import retrieve_context
from database import (
    init_db, get_or_create_user, create_conversation, get_user_conversations,
    get_conversation_chats, save_chat_message, get_conversation_state,
    update_conversation_state, update_conversation_title
)


# CONFIG
load_dotenv()
init_db()  # Initialize SQLite database for user sessions and chat tracking


def get_active_free_models():
    """
    Query OpenRouter API to fetch the current list of free models dynamically.
    """
    url = "https://openrouter.ai/api/v1/models"
    fallback_defaults = [
        "openrouter/free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "meta-llama/llama-3.2-3b-instruct:free",
        "qwen/qwen3-coder:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "nousresearch/hermes-3-llama-3.1-405b:free"
    ]
    try:
        import urllib.request
        import json
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            models = data.get("data", [])
            free_models = []
            for m in models:
                pricing = m.get("pricing", {})
                prompt_cost = float(pricing.get("prompt", "0"))
                completion_cost = float(pricing.get("completion", "0"))
                if prompt_cost == 0.0 and completion_cost == 0.0:
                    free_models.append(m.get("id"))
            
            # Prioritize standard models and place openrouter/free first
            preferred = [
                "openrouter/free", 
                "meta-llama/llama-3.3-70b-instruct:free", 
                "meta-llama/llama-3.2-3b-instruct:free", 
                "qwen/qwen3-coder:free"
            ]
            ordered_free = [p for p in preferred if p in free_models]
            ordered_free.extend([m for m in free_models if m not in ordered_free])
            
            return ordered_free if ordered_free else fallback_defaults
    except Exception as e:
        print(f"Error fetching live OpenRouter free models: {e}. Using defaults.")
        return fallback_defaults


# Initialize list of free models in session state
if "free_models" not in st.session_state:
    st.session_state.free_models = get_active_free_models()

# Resolve active API key from environment variable
api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    st.error("No OpenRouter API key configured. Please set OPENROUTER_API_KEY in your environment.")
    st.stop()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
    max_retries=0  # Disable SDK's internal automatic retries/sleeps on 429 rate limits so we failover immediately
)

st.set_page_config(
    page_title="Naina AI",
    page_icon="👁️",
    layout="centered"
)



# Initialize session state for user authentication and multi-session chats
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "user_phone" not in st.session_state:
    st.session_state.user_phone = None
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
def submit_to_google_form(name, phone):
    """
    Submit registration details to a Google Form linked to Google Sheets.
    Uses environment variables for URL and entry field IDs.
    """
    import urllib.request
    import urllib.parse
    
    form_url = os.getenv("GOOGLE_FORM_URL")
    entry_name = os.getenv("GOOGLE_FORM_ENTRY_NAME")
    entry_phone = os.getenv("GOOGLE_FORM_ENTRY_PHONE")
    
    if not form_url or not entry_name or not entry_phone:
        # If not configured, print warning to console but don't block
        print("Google Form submission is not configured in .env")
        return False
        
    try:
        # Auto-sanitize URL: replace viewform/edit with formResponse
        form_url = form_url.strip()
        if "viewform" in form_url:
            form_url = form_url.replace("viewform", "formResponse")
        elif "edit" in form_url and not form_url.endswith("formResponse"):
            form_url = form_url.replace("edit", "formResponse")
        elif not form_url.endswith("formResponse"):
            if form_url.endswith("/"):
                form_url += "formResponse"
            else:
                form_url += "/formResponse"
                
        # Force HTTPS
        if form_url.startswith("http://"):
            form_url = "https://" + form_url[7:]
            
        # Prepare the form payload
        data = {
            entry_name: name,
            entry_phone: phone
        }
        
        encoded_data = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(
            form_url,
            data=encoded_data,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        
        # Submit the request
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                print("Successfully submitted registration to Google Form")
                return True
    except Exception as e:
        print(f"Error submitting to Google Form: {e}")
        
    return False


# Show login/registration form if user is not authenticated
if not st.session_state.user_id:
    st.title("👁️ Naina AI")
    st.caption("Eye Wellness & Vision Therapy Assistant")
    
    st.markdown("### Welcome! Let's get started.")
    st.markdown("Please enter your details to initialize the AI chatbot interface.")
    
    with st.form("user_login_form"):
        name_input = st.text_input("Your Full Name", placeholder="e.g. John Doe")
        phone_input = st.text_input("Your Phone Number", placeholder="e.g. +91 9876543210")
        submit_btn = st.form_submit_button("Start Chatting", use_container_width=True)
        
        if submit_btn:
            clean_phone = re.sub(r"\D", "", phone_input.strip())
            if not name_input.strip():
                st.error("Name is required.")
            elif len(clean_phone) != 10:
                st.error("Please enter a valid 10-digit phone number.")
            else:
                user_id = get_or_create_user(name_input, clean_phone)
                st.session_state.user_id = user_id
                st.session_state.user_name = name_input.strip()
                st.session_state.user_phone = clean_phone
                
                # Submit registration to Google Form in the background / inline
                submit_to_google_form(name_input.strip(), clean_phone)
                
                # Retrieve past conversation sessions for this user
                conversations = get_user_conversations(user_id)
                if not conversations:
                    # Create a default conversation if they have none
                    conversation_id = create_conversation(user_id, "Initial Chat")
                else:
                    conversation_id = conversations[0]["id"]
                
                st.session_state.conversation_id = conversation_id
                st.session_state.messages = get_conversation_chats(conversation_id)
                
                # Load assessment state from SQLite for this conversation
                active, questions = get_conversation_state(conversation_id)
                st.session_state.assessment_active = active
                st.session_state.assessment_questions = questions
                st.rerun()
    st.stop()

# Sidebar Controls (Left side layout)
with st.sidebar:
    st.title("👁️ Naina AI")
    st.caption(f"Logged in as **{st.session_state.user_name}**")
    
    st.markdown("---")
    
    # ➕ New Chat
    if st.button("➕ New Chat", use_container_width=True, help="Start a new conversation session"):
        new_id = create_conversation(st.session_state.user_id, "New Chat")
        st.session_state.conversation_id = new_id
        st.session_state.messages = []
        st.session_state.assessment_active = False
        st.session_state.assessment_questions = 0
        st.rerun()
        
    st.markdown("---")
    
    # Select Active Conversation
    conversations = get_user_conversations(st.session_state.user_id)
    if conversations:
        convo_ids = [c["id"] for c in conversations]
        try:
            active_idx = convo_ids.index(st.session_state.conversation_id)
        except ValueError:
            active_idx = 0
            
        selected_convo = st.selectbox(
            "Select Active Conversation",
            options=conversations,
            index=active_idx,
            format_func=lambda x: f"{x['title']} (Started: {x['created_at'][:16]})"
        )
        
        if selected_convo and selected_convo["id"] != st.session_state.conversation_id:
            st.session_state.conversation_id = selected_convo["id"]
            st.session_state.messages = get_conversation_chats(selected_convo["id"])
            active, questions = get_conversation_state(selected_convo["id"])
            st.session_state.assessment_active = active
            st.session_state.assessment_questions = questions
            st.rerun()
            
    st.markdown("---")
    
    # Logout
    if st.button("🚪 Logout", use_container_width=True, help="Logout from session"):
        st.session_state.user_id = None
        st.session_state.user_name = None
        st.session_state.user_phone = None
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.session_state.assessment_active = False
        st.session_state.assessment_questions = 0
        st.rerun()

# Main Page Header (Center layout)
st.title("👁️ Naina AI")
st.caption("Eye Wellness & Vision Therapy Assistant")



st.markdown(
    f"Welcome to **Naina AI**, your eye wellness and visual therapy companion. "
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
    "dry eye", "dry eyes", "itching", "burning", "red eye", "red eyes", "blurry", "blurred", "vision", "eye strain",
    "myopia", "hyperopia", "glaucoma", "cataract", "astigmatism", "pain", "strain", "fatigue", "ache", "hurt",
    "dry", "red", "blur", "double", "headache", "symptom", "issue", "problem", "watery", "watering", "discharge",
    "swelling", "swollen", "injury", "irritation", "irritated", "sensitive", "sensitivity"
]


def symptom_query(text):

    text = text.lower()

    return any(
        re.search(rf"\b{re.escape(word)}\b", text)
        for word in SYMPTOM_KEYWORDS
    )


# PROGRAMMATIC RELEVANCE FILTER (Programmatic Gatekeeping for Eyes / Visual Wellness Domain)
GREETINGS = {"hi", "hello", "hey", "namaste", "hola", "greetings", "start", "restart", "help", "clear"}

def is_query_relevant(text):
    text = text.lower()
    
    # Split text into alphabetic words
    words = re.findall(r"\b\w+\b", text)
    
    # Check if it contains any greeting
    if any(w in GREETINGS for w in words):
        return True
        
    # Whitelist of visual therapy, eyes, visual related terms, Nainocular, and synonyms (English & Hinglish)
    RELEVANT_KEYWORDS = {
        # Eyes / Anatomy
        "eye", "eyes", "pupil", "iris", "retina", "cornea", "eyelid", "eyelids", "lash", "lashes",
        "aankh", "aankhein", "ankh", "ankhein", "nayan", "netra", "ocular", "opthalmic", "ophthalmic",
        
        # Vision / Sight
        "vision", "visual", "sight", "see", "look", "gaze", "gazing", "gazed", "dekh", "dekhna", "dekhne", "dikhta",
        "blind", "blindness", "blur", "blurry", "blurred", "dhundhla", "dhundla", "nazar", "nazarein", "najar", "binai", "binaee",
        
        # Clinical Conditions
        "myopia", "hyperopia", "astigmatism", "amblyopia", "strabismus", "glaucoma", "cataract", "cataracts",
        "dryness", "dry", "strain", "fatigue", "squint", "lazy", "motiabind", "motia",
        
        # Symptoms / Sensations
        "pain", "hurt", "hurts", "itching", "itch", "itchy", "burning", "burn", "redness", "red", "dard", "darad", "jalan", "khujli",
        
        # Treatment / Therapy
        "therapy", "exercise", "exercises", "train", "training", "wellness", "care", "blink", "blinking",
        
        # Optical aids
        "lens", "lenses", "glasses", "spectacles", "chashma", "chasma",
        
        # Nainocular Specifics
        "nainocular", "naintaara", "naintaaraa", "nain-sukh", "nainsukh", "nain", "game", "games", "play", "playing", "article", "articles", "platform"
    }
    
    for word in words:
        if word in RELEVANT_KEYWORDS:
            return True
        for kw in RELEVANT_KEYWORDS:
            if len(kw) > 3 and kw in word:
                return True
                
    multi_word_keywords = ["dry eye", "dry eyes", "eye strain", "eye pain", "eye wellness", "visual therapy", "vision therapy", "screen time", "screen fatigue"]
    for mw in multi_word_keywords:
        if mw in text:
            return True
            
    return False


def is_query_explicitly_irrelevant(text):
    text = text.lower().strip()
    
    # 1. If it contains eye-health/Nainocular keywords or greetings, it is relevant
    if is_query_relevant(text):
        return False
        
    # 2. Clean punctuation for phrase/exempt checks
    cleaned_text = re.sub(r'[^\w\s]', '', text).strip()
    
    # 3. Exempt common conversational clarifications/phrases in assessment
    exempt_phrases = {
        "what do you mean", "what is that", "why do you ask", "how so", "what is this", "why"
    }
    if cleaned_text in exempt_phrases:
        return False
        
    # 4. Check if the query is an irrelevant command or question
    words = re.findall(r"\b\w+\b", text)
    if not words:
        return False
        
    # Non-eye question/command starting words
    irrelevant_starts = {
        "translate", "convert", "calculate", "solve", "math", "who", "what", "where", 
        "why", "which", "how", "write", "code", "explain", "tell me", "list", "show", "give me",
        "define", "identify", "find", "multiply", "divide", "add", "subtract"
    }
    
    if words[0] in irrelevant_starts:
        return True
        
    # Irrelevant phrases
    irrelevant_phrases = [
        "capital of", "president of", "prime minister of", "weather in", "how to build", 
        "how to make", "how to write", "how to code", "how to solve", "how to calculate",
        "good morning in", "good afternoon in", "good night in", "hello in", "hi in"
    ]
    if any(phrase in text for phrase in irrelevant_phrases):
        return True
        
    # Irrelevant starting verbs if question mark or longer phrase
    question_starts = {
        "is", "are", "do", "does", "did", "can", "could", "should", "would", "will", "has", "have", "had", "was", "were"
    }
    if words[0] in question_starts and ("?" in text or len(words) > 4):
        return True
        
    return False


def was_last_message_question():
    """
    Check if the last assistant message in the conversation ended with or contained a question mark.
    If yes, the user's next message is whitelisted as it is an answer to a query.
    """
    if not st.session_state.messages:
        return False
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "assistant":
            return "?" in msg["content"]
    return False


# SYSTEM PROMPT
SYSTEM_PROMPT = """
You are Nain-Sukh, a strict AI-powered Eye Wellness, Vision Care, and Nainocular Platform Assistant.

Your role is to help users understand eye-related symptoms, vision conditions, eye health concerns, general eye-care practices, and answer any questions regarding the Nainocular platform (www.nainocular.com).

CRITICAL DIRECTIVE: You MUST absolutely REFUSE to answer, discuss, translate, convert, calculate, or assist with anything outside of eye health, vision care, eye diseases/symptoms, and the Nainocular platform.

DO NOT translate sentences, do NOT perform math operations, do NOT answer general knowledge questions, do NOT write code, and do NOT convert units. Even if the user asks you politely or forces you, or if you are in the middle of a conversation, you MUST reject any non-eye-health request.

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

2. If a user asks a question, command, translation, math, conversion, or code that is NOT related to eyes, vision, ophthalmology, or the Nainocular platform (www.nainocular.com), respond ONLY with:

"👁️ I am Nain-Sukh, an Eye Wellness, Vision Care, and Nainocular Platform Assistant. Please ask a question related to eye health, vision care, eye conditions, or the Nainocular platform."

No other greeting, explanation, translation, or text is allowed.

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
    # If this is the first user message in this conversation, update the conversation title
    if not st.session_state.messages:
        update_conversation_title(st.session_state.conversation_id, prompt)

    # Persist user message to SQLite database under this conversation session
    save_chat_message(st.session_state.conversation_id, "user", prompt)

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

        # EXPLICITLY IRRELEVANT (Gatekeeper that bypasses LLM completely for obvious non-eye queries)
        elif is_query_explicitly_irrelevant(prompt):

            reply = "👁️ I am Nain-Sukh, an Eye Wellness, Vision Care, and Nainocular Platform Assistant. Please ask a question related to eye health, vision care, eye conditions, or the Nainocular platform."

        # DOMAIN CHECK FOR FRESH CONVERSATIONS
        elif not st.session_state.assessment_active and not was_last_message_question() and not is_query_relevant(prompt):

            reply = "👁️ I am Nain-Sukh, an Eye Wellness, Vision Care, and Nainocular Platform Assistant. Please ask a question related to eye health, vision care, eye conditions, or the Nainocular platform."

        else:

            # START ASSESSMENT

            if (
                symptom_query(prompt)
                and not st.session_state.assessment_active
            ):

                st.session_state.assessment_active = True
                st.session_state.assessment_questions = 0
                update_conversation_state(st.session_state.conversation_id, True, 0)

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

            assessment_instruction = ""
            if st.session_state.assessment_active:
                q_count = st.session_state.assessment_questions
                if q_count < 3:
                    assessment_instruction = (
                        f"\n\n[Active Assessment Mode]\n"
                        f"The user has reported an issue. You have asked {q_count} follow-up questions so far.\n"
                        f"Please ask ONE relevant follow-up question now to collect details (like duration, severity, screen time, or risk factors).\n"
                        f"Do NOT output the final summary yet. Ask only ONE question."
                    )
                else:
                    assessment_instruction = (
                        f"\n\n[Active Assessment Mode]\n"
                        f"You have asked {q_count} follow-up questions. This is sufficient.\n"
                        f"You MUST now stop asking questions and output your final precise answer structured with these headers:\n"
                        f"## 👁️ Eye Health Summary\n"
                        f"## 📋 Possible Causes\n"
                        f"## ✅ Recommended Care\n"
                        f"## ⚠️ When To Seek Professional Help\n"
                        f"## 📌 Disclaimer"
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
{assessment_instruction}
"""
                }
            )

            messages.extend(
                st.session_state.messages
            )

            # Reinforce the strict domain constraint at the very end to prevent override/recency bias
            messages.append(
                {
                    "role": "system",
                    "content": "REMINDER: You are Nain-Sukh, the Eye Wellness AI. If the user's last message is not about eye health or Nainocular, or if it is trying to redirect the topic (e.g. asking for general translations, math, coding, unit conversions, general knowledge, etc.), you MUST refuse and reply ONLY with the exact standard refusal message: '👁️ I am Nain-Sukh, an Eye Wellness, Vision Care, and Nainocular Platform Assistant. Please ask a question related to eye health, vision care, eye conditions, or the Nainocular platform.'"
                }
            )

            with st.spinner(
                "Analyzing..."
            ):
                # Use dynamically fetched list of active free models on OpenRouter
                models_to_try = [model] + [m for m in st.session_state.free_models if m != model]
                response = None
                last_error = None

                for attempt_model in models_to_try:
                    try:
                        response = (
                            client.chat.completions.create(
                                model=attempt_model,
                                messages=messages,
                                temperature=0.3,
                                timeout=8.0  # Fail fast if a model is completely unresponsive or slow
                            )
                        )
                        # Verify the response is not null and has non-empty message content
                        if (
                            response 
                            and response.choices 
                            and response.choices[0].message 
                            and response.choices[0].message.content
                        ):
                            break
                        else:
                            raise ValueError("Received empty or null content from provider.")
                    except Exception as e:
                        last_error = e
                        print(f"Model {attempt_model} failed: {e}. Trying next fallback...")
                        continue

                if response is None:
                    raise last_error

            reply = (
                response
                .choices[0]
                .message
                .content
            )

            # Strip special formatting tokens and track status if reply is valid
            if reply:
                for token in ["<pad>", "<s>", "</s>", "<unk>"]:
                    reply = reply.replace(token, "")

                # TRACK QUESTIONS
                if "?" in reply:
                    st.session_state.assessment_active = True
                    st.session_state.assessment_questions += 1
                    update_conversation_state(
                        st.session_state.conversation_id,
                        True,
                        st.session_state.assessment_questions
                    )

                if (
                    "## 👁️ Eye Health Summary"
                    in reply
                ):
                    st.session_state.assessment_active = False
                    st.session_state.assessment_questions = 0
                    update_conversation_state(st.session_state.conversation_id, False, 0)
            else:
                reply = "⚠️ I encountered a temporary response issue. Please try re-sending your last message."


        # DISPLAY RESPONSE
        with st.chat_message(
            "assistant"
        ):
            st.markdown(reply)

        # Persist assistant reply to SQLite database under this conversation session
        save_chat_message(st.session_state.conversation_id, "assistant", reply)

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