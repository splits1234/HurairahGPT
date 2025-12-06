# Copyright (c) 2025 Hurairah
# All Rights Reserved. Proprietary Software.
# Legal matters handled by parent/guardian until age 18.
# Governed by Pakistan law (Rawalpindi jurisdiction).
import re
import uuid
import traceback
from flask import Flask, render_template, request, redirect, session, url_for, jsonify, Response, stream_with_context
from openai import OpenAI
import json
import os
import time
from datetime import datetime
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

app = Flask(__name__)
app.secret_key = "supersecretkey"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

MOBILE_UA_RE = re.compile(r"android|iphone|ipad|ipod|blackberry|iemobile|windows phone|opera mini|mobile", re.I)

client = OpenAI(
    api_key="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",
    base_url="https://openrouter.ai/api/v1"
)

MODEL = "deepseek/deepseek-chat"  # OpenRouter free model
PERSONALITIES = {
    "default": "You are a helpful AI assistant.",
    "funny": "You are sarcastic, witty, and always crack jokes.",
    "islamic": "You answer with Islamic knowledge, Quran, and Hadith (avoid opinions).",
    "coder": "You are a senior programmer. Answer with code first, minimal talk."
}


def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def send_email(to_email, subject, body):
    sender_email = "hurairahgpt.devteam@gmail.com"
    sender_password = "zexs xnud wwoq rlxe"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True, "Email sent successfully."
    except Exception as e:
        return False, str(e)


def find_credentials(email_to_find):
    path = Path(BASE_DIR) / "credentials.txt"
    path.touch(exist_ok=True)
    text = path.read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for sep in [":", ",", " ", "\t"]:
            if sep in line:
                parts = [p.strip() for p in line.split(sep, 1)]
                if len(parts) >= 2 and parts[0].lower() == email_to_find.lower():
                    return parts[1]
    return None


def retry_request(func, retries=3, delay=1, fallback="Unavailable"):
    last_error = None
    for attempt in range(retries):
        try:
            return func()
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                # Log the error on the last attempt with full traceback
                print(f"Error after {retries} attempts: {type(e).__name__}: {str(e)}")
                print(f"Traceback: {traceback.format_exc()}")
    return fallback


def get_islamic_date():
    def _call():
        res = requests.get("http://api.aladhan.com/v1/gToH",
                           params={"date": datetime.now().strftime("%d-%m-%Y")},
                           timeout=5)
        hijri = res.json()["data"]["hijri"]["date"]
        return f"Islamic date: {hijri}"
    return retry_request(_call, fallback="Islamic date unavailable.")


def excontext():
    return f"your in an app called hurairahgpt. website is talktohurairah.com your developed by hurairah and hurairah is a solo develeper building and mantaining this project you can contect us at hurairahgpt.devteam@gmail.com. He is a male"


def get_news_headline():
    def _call():
        res = requests.get("https://newsapi.org/v2/top-headlines",
                           params={"country": "pk",
                                   "apiKey": "418ef79bb38a4535b08a51a4b48a8c4b"},
                           timeout=5)
        data = res.json()
        if data.get("status") == "ok" and data.get("totalResults", 0) > 0:
            return f"Top news: {data['articles'][0]['title']}"
        return "No news articles found."
    return retry_request(_call, fallback="News unavailable.")


def migrate_user_to_sessions(user_data):
    """Migrate old user data structure to new sessions structure"""
    if "sessions" in user_data:
        return user_data  # Already migrated
    
    # Migrate old history to a default session
    session_id = str(uuid.uuid4())
    old_history = user_data.get("history", [])
    
    user_data["sessions"] = {
        session_id: {
            "name": "Chat 1",
            "history": old_history,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    user_data["active_session"] = session_id
    
    # Remove old history field
    if "history" in user_data:
        del user_data["history"]
    
    return user_data


def get_user_data_with_sessions(gmail):
    """Get user data and ensure it has sessions structure"""
    users = load_users()
    user_data = users.get(gmail, {
        "sessions": {},
        "active_session": None,
        "theme": "dark",
        "personality": "default"
    })
    
    # Migrate if needed
    user_data = migrate_user_to_sessions(user_data)
    
    # Ensure active_session exists and is valid
    if not user_data.get("active_session") or user_data["active_session"] not in user_data.get("sessions", {}):
        # Create default session if none exists
        if not user_data.get("sessions"):
            session_id = str(uuid.uuid4())
            user_data["sessions"] = {
                session_id: {
                    "name": "Chat 1",
                    "history": [],
                    "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }
            user_data["active_session"] = session_id
        else:
            # Use first available session
            user_data["active_session"] = list(user_data["sessions"].keys())[0]
    
    users[gmail] = user_data
    save_users(users)
    
    return user_data


def get_active_session_history(user_data):
    """Get history from active session"""
    active_id = user_data.get("active_session")
    if not active_id:
        return []
    sessions = user_data.get("sessions", {})
    active_session = sessions.get(active_id, {})
    return active_session.get("history", [])


@app.route("/")
def root():
    if "gmail" not in session:
        return redirect(url_for("login"))

    ua = request.headers.get("User-Agent", "")
    is_mobile = bool(MOBILE_UA_RE.search(ua))

    if request.args.get("mobile") in ("1", "true", "yes"):
        is_mobile = True
    if request.args.get("desktop") in ("1", "true", "yes"):
        is_mobile = False

    user_data = get_user_data_with_sessions(session["gmail"])
    history = get_active_session_history(user_data)
    sessions_list = user_data.get("sessions", {})
    active_session_id = user_data.get("active_session")

    if is_mobile:
        return render_template("moindex.html", 
                             gmail=session["gmail"], 
                             history=history, 
                             theme=user_data["theme"],
                             sessions=sessions_list,
                             active_session=active_session_id)
    return render_template("index.html", 
                         gmail=session["gmail"], 
                         history=history, 
                         theme=user_data["theme"],
                         sessions=sessions_list,
                         active_session=active_session_id)


@app.route("/slipt")
def slipt():
    return render_template("slipt.html")


@app.route("/main")
def main_index():
    if "gmail" not in session:
        return redirect(url_for("login"))
    user_data = get_user_data_with_sessions(session["gmail"])
    history = get_active_session_history(user_data)
    sessions_list = user_data.get("sessions", {})
    active_session_id = user_data.get("active_session")
    return render_template("index.html",
                           gmail=session["gmail"],
                           history=history,
                           theme=user_data["theme"],
                           sessions=sessions_list,
                           active_session=active_session_id)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        gmail = request.form.get("gmail", "").strip()
        password = request.form.get("password", "").strip()

        if not gmail or not password:
            return render_template("login.html", error="Please fill out all fields.")

        # Handle guest account
        if gmail.lower() == "guest@gmail.com" and password == "guest":
            session["gmail"] = "guest@gmail.com"
            users = load_users()
            if "guest@gmail.com" not in users:
                session_id = str(uuid.uuid4())
                users["guest@gmail.com"] = {
                    "sessions": {
                        session_id: {
                            "name": "Chat 1",
                            "history": [],
                            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    },
                    "active_session": session_id,
                    "theme": "dark",
                    "personality": "default"
                }
                save_users(users)
            return redirect(url_for("root"))

        # Regular account login
        stored_pw = find_credentials(gmail)
        if not stored_pw:
            return render_template("login.html", error="Account not found. Please sign up first.")

        if stored_pw != password:
            return render_template("login.html", error="Incorrect password.")

        # success
        session["gmail"] = gmail
        users = load_users()
        if gmail not in users:
            session_id = str(uuid.uuid4())
            users[gmail] = {
                "sessions": {
                    session_id: {
                        "name": "Chat 1",
                        "history": [],
                        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                },
                "active_session": session_id,
                "theme": "dark",
                "personality": "default"
            }
            save_users(users)
        return redirect(url_for("root"))

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        gmail = request.form.get("gmail", "").strip()
        password = request.form.get("password", "").strip()

        if not gmail or not password:
            return render_template("signup.html", error="Please fill out all fields.")

        credentials_path = os.path.join(BASE_DIR, "credentials.txt")
        os.makedirs(os.path.dirname(credentials_path), exist_ok=True)

        # Check if the user already exists
        existing_pw = find_credentials(gmail)
        if existing_pw:
            return render_template("signup.html", error="Account already exists. Please log in.")

        # Register the new account
        with open(credentials_path, "a", encoding="utf-8") as f:
            f.write(f"{gmail}:{password}\n")

        # Add new user record with sessions structure
        users = load_users()
        session_id = str(uuid.uuid4())
        users[gmail] = {
            "sessions": {
                session_id: {
                    "name": "Chat 1",
                    "history": [],
                    "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            },
            "active_session": session_id,
            "theme": "dark",
            "personality": "default"
        }
        save_users(users)

        session["gmail"] = gmail
        return redirect(url_for("root"))

    return render_template("signup.html")




@app.route("/logout")
def logout():
    session.pop("gmail", None)
    return redirect(url_for("login"))


@app.route("/chat", methods=["POST"])
def chat():
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_message = request.json.get("message", "")
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    users = load_users()
    user_data = get_user_data_with_sessions(session["gmail"])
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    active_session_id = user_data.get("active_session")
    if not active_session_id or active_session_id not in user_data.get("sessions", {}):
        return jsonify({"error": "No active session"}), 400

    active_session = user_data["sessions"][active_session_id]
    history = active_session.get("history", [])

    if user_message == "__CLEAR__":
        active_session["history"] = []
        users[session["gmail"]] = user_data
        save_users(users)
        return jsonify({"response": "Chat history cleared."})

    # Check if streaming is requested
    stream = request.json.get("stream", False)

    user_personality = user_data.get("personality", "default")
    system_content = PERSONALITIES.get(user_personality, PERSONALITIES["default"]) + "\n\n" + "\n".join([
        f"Today is {datetime.now().strftime('%A, %B %d, %Y')}.",
        get_islamic_date(),
        get_news_headline(),
        excontext()
    ])

    messages = [{"role": "system", "content": system_content}]
    for entry in history:
        role = "user" if entry["sender"] == "user" else "assistant"
        messages.append({"role": role, "content": entry["content"]})
    messages.append({"role": "user", "content": user_message})

    # Save user message immediately
    history.append({"content": user_message, "sender": "user", "time": timestamp})

    if stream:
        # Streaming response
        def generate():
            full_response = ""
            try:
                stream_response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    stream=True,
                    timeout=60
                )
                
                for chunk in stream_response:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content:
                            content = delta.content
                            full_response += content
                            # Send each chunk as SSE
                            yield f"data: {json.dumps({'chunk': content, 'done': False})}\n\n"
                
                # Send completion signal
                yield f"data: {json.dumps({'chunk': '', 'done': True, 'full_response': full_response})}\n\n"
                
                # Save the full response to history
                history.append({"content": full_response, "sender": "bot", "time": timestamp})
                if len(history) > 400:
                    active_session["history"] = history[-400:]
                else:
                    active_session["history"] = history
                
                users[session["gmail"]] = user_data
                save_users(users)
                
            except Exception as e:
                error_msg = f"AI service unavailable, please try again later."
                print(f"Streaming API Error: {type(e).__name__}: {str(e)}")
                yield f"data: {json.dumps({'chunk': '', 'done': True, 'error': error_msg})}\n\n"
                # Save error message
                history.append({"content": error_msg, "sender": "bot", "time": timestamp})
                active_session["history"] = history
                users[session["gmail"]] = user_data
                save_users(users)

        return Response(stream_with_context(generate()), mimetype='text/event-stream')
    else:
        # Non-streaming response (backward compatibility)
        def call_ai():
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    timeout=30
                )
                if not response.choices or len(response.choices) == 0:
                    raise Exception("No response choices returned from API")
                return response.choices[0].message.content
            except Exception as e:
                error_msg = f"API Error: {type(e).__name__}: {str(e)}"
                print(error_msg)
                print(f"Model: {MODEL}, Base URL: {client.base_url}")
                raise

        ai_reply = retry_request(call_ai, retries=2, delay=2, fallback="AI service unavailable, please try again later.")
        
        if ai_reply == "AI service unavailable, please try again later.":
            print(f"Failed to get AI response after retries.")
            print(f"Please check:")
            print(f"  1. API key is valid: {client.api_key[:20]}...")
            print(f"  2. Model name is correct: {MODEL}")
            print(f"  3. Network connection to {client.base_url}")
            print(f"  4. OpenRouter API status")

        history.append({"content": ai_reply, "sender": "bot", "time": timestamp})
        if len(history) > 400:
            active_session["history"] = history[-400:]
        else:
            active_session["history"] = history

        users[session["gmail"]] = user_data
        save_users(users)

        return jsonify({"response": ai_reply})


@app.route("/theme", methods=["POST"])
def update_theme():
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    theme = request.json.get("theme")
    users = load_users()
    if session["gmail"] in users:
        users[session["gmail"]]["theme"] = theme
        save_users(users)
    return jsonify({"success": True})


@app.route("/personality", methods=["POST"])
def update_personality():
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    personality = request.json.get("personality", "default")
    users = load_users()
    if session["gmail"] in users:
        users[session["gmail"]]["personality"] = personality
        save_users(users)
    return jsonify({"success": True})


@app.route("/moindex")
def moindex():
    if "gmail" not in session:
        return redirect(url_for("login"))
    user_data = get_user_data_with_sessions(session["gmail"])
    history = get_active_session_history(user_data)
    sessions_list = user_data.get("sessions", {})
    active_session_id = user_data.get("active_session")
    return render_template("moindex.html",
                           gmail=session["gmail"],
                           history=history,
                           theme=user_data["theme"],
                           sessions=sessions_list,
                           active_session=active_session_id)


@app.route("/forgot", methods=["GET"])
def forgot_get():
    return render_template("reset.html")


@app.route("/forgot", methods=["POST"])
def forgot_post():
    email = request.form.get("email", "").strip()
    if not email:
        return render_template("reset.html", error="Please enter your email.")

    users = load_users()
    password_found = None
    if email in users and users[email].get("password"):
        password_found = users[email]["password"]
    else:
        pw = find_credentials(email)
        if pw:
            password_found = pw

    if not password_found:
        return render_template("reset.html", sent=True)

    subject = "HurairahGPT — Your account credentials"
    body = f"Hello,\n\nYou requested your account credentials for HurairahGPT.\n\nEmail: {email}\nPassword: {password_found}\n\nIf you did not request this, ignore this email.\n\n— HurairahGPT Team"

    ok, msg = send_email(email, subject, body)
    if ok:
        return render_template("reset.html", sent=True)
    else:
        return render_template("reset.html", error="Failed to send email. " + msg)


@app.route("/sessions/create", methods=["POST"])
def create_session():
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    users = load_users()
    user_data = get_user_data_with_sessions(session["gmail"])
    
    session_id = str(uuid.uuid4())
    session_name = request.json.get("name", "").strip() or f"Chat {len(user_data.get('sessions', {})) + 1}"
    
    user_data.setdefault("sessions", {})
    user_data["sessions"][session_id] = {
        "name": session_name,
        "history": [],
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    user_data["active_session"] = session_id
    
    users[session["gmail"]] = user_data
    save_users(users)
    
    return jsonify({"success": True, "session_id": session_id, "sessions": user_data["sessions"]})


@app.route("/sessions/switch", methods=["POST"])
def switch_session():
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    session_id = request.json.get("session_id")
    if not session_id:
        return jsonify({"error": "No session_id provided"}), 400
    
    users = load_users()
    user_data = get_user_data_with_sessions(session["gmail"])
    
    if session_id not in user_data.get("sessions", {}):
        return jsonify({"error": "Session not found"}), 404
    
    user_data["active_session"] = session_id
    users[session["gmail"]] = user_data
    save_users(users)
    
    active_session = user_data["sessions"][session_id]
    return jsonify({
        "success": True,
        "history": active_session.get("history", []),
        "sessions": user_data["sessions"]
    })


@app.route("/sessions/delete", methods=["POST"])
def delete_session():
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    session_id = request.json.get("session_id")
    if not session_id:
        return jsonify({"error": "No session_id provided"}), 400
    
    users = load_users()
    user_data = get_user_data_with_sessions(session["gmail"])
    
    if session_id not in user_data.get("sessions", {}):
        return jsonify({"error": "Session not found"}), 404
    
    sessions = user_data.get("sessions", {})
    if len(sessions) <= 1:
        return jsonify({"error": "Cannot delete the last session"}), 400
    
    # Delete the session
    del sessions[session_id]
    
    # If it was the active session, switch to another one
    if user_data.get("active_session") == session_id:
        user_data["active_session"] = list(sessions.keys())[0]
    
    users[session["gmail"]] = user_data
    save_users(users)
    
    active_session = user_data["sessions"][user_data["active_session"]]
    return jsonify({
        "success": True,
        "history": active_session.get("history", []),
        "sessions": user_data["sessions"],
        "active_session": user_data["active_session"]
    })


@app.route("/sessions/rename", methods=["POST"])
def rename_session():
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    session_id = request.json.get("session_id")
    new_name = request.json.get("name", "").strip()
    
    if not session_id or not new_name:
        return jsonify({"error": "Missing session_id or name"}), 400
    
    users = load_users()
    user_data = get_user_data_with_sessions(session["gmail"])
    
    if session_id not in user_data.get("sessions", {}):
        return jsonify({"error": "Session not found"}), 404
    
    user_data["sessions"][session_id]["name"] = new_name
    users[session["gmail"]] = user_data
    save_users(users)
    
    return jsonify({"success": True, "sessions": user_data["sessions"]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
