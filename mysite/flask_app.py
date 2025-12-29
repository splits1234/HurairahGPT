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
import base64
from datetime import datetime
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from flask import send_from_directory
from PIL import Image
import io



app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
IMAGES_DIR = os.path.join(BASE_DIR, "user_images")
os.makedirs(IMAGES_DIR, exist_ok=True)


if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

MOBILE_UA_RE = re.compile(r"android|iphone|ipad|ipod|blackberry|iemobile|windows phone|opera mini|mobile", re.I)

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
)

MODEL = "deepseek/deepseek-chat"  # OpenRouter free model (text/chat)
# At the top of app.py
IMG_MODEL = "black-forest-labs/flux-1-schnell"  # ByteDance Seedream 4.5 for image generation  # ByteDance Seedream 4.5 for image generation

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
    sender_email = os.getenv("SMTP_EMAIL")
    sender_password = os.getenv("SMTP_PASSWORD")

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




def excontext():
    return f"your in an app called hurairahgpt. website is talktohurairah.com your developed by hurairah and hurairah is a solo develeper building and mantaining this project you can contect us at hurairahgpt.devteam@gmail.com. He is a male"





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


@app.route("/robots.txt")
def robots():
    return send_from_directory(".", "robots.txt")

@app.route("/images/<filename>")
def serve_image(filename):
    return send_from_directory(IMAGES_DIR, filename)



@app.route("/deletedata")
def deletedata():
    return render_template("deletedata.html")


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
                error_msg = "AI service unavailable, please try again later."
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
            print("Failed to get AI response after retries.")
            print("Please check:")
            print(f"  1. API key is valid: {client.api_key[:20]}...")
            print(f"  2. Model name is correct: {MODEL}")
            print(f"  3. Network connection to {client.base_url}")
            print("  4. OpenRouter API status")

        history.append({"content": ai_reply, "sender": "bot", "time": timestamp})
        if len(history) > 400:
            active_session["history"] = history[-400:]
        else:
            active_session["history"] = history

        users[session["gmail"]] = user_data
        save_users(users)

        return jsonify({"response": ai_reply})


def create_thumbnail(img_data, max_size=(150, 150)):
    """Create a small thumbnail from image data"""
    try:
        # Open image from bytes
        img = Image.open(io.BytesIO(img_data))
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
        
        # Create thumbnail
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert to JPEG for smaller size
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85, optimize=True)
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return img_str
    except Exception as e:
        print(f"Thumbnail creation failed: {e}")
        return None



@app.route("/image", methods=["POST"])
def image_gen():
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    prompt = request.json.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "No prompt"}), 400

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "google/gemini-2.5-flash-image-preview",
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["image", "text"]
    }

    try:
        print(f"Sending image generation request for prompt: {prompt}")
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        
        print(f"Response received, checking structure...")
        
        if "choices" not in data or len(data["choices"]) == 0:
            return jsonify({"error": "No choices in response"}), 500
            
        message = data["choices"][0]["message"]
        
        # Check if images array exists
        if "images" not in message or len(message["images"]) == 0:
            print("No images array in response")
            return jsonify({"error": "No images in response"}), 500
        
        # Get the first image object
        first_image = message["images"][0]
        print(f"First image object: {first_image}")
        
        # Check the structure - it should have "image_url" with "url" inside
        if "image_url" not in first_image or "url" not in first_image["image_url"]:
            print(f"Unexpected image structure: {first_image}")
            return jsonify({"error": "Unexpected image format"}), 500
        
        # Get the data URL
        data_url = first_image["image_url"]["url"]
        print(f"Got data URL (first 100 chars): {data_url[:100]}...")
        
        # Extract base64 from data URL
        if not data_url.startswith("data:image/"):
            print(f"Not a data URL: {data_url[:100]}...")
            return jsonify({"error": "Not a data URL"}), 500
        
        # Split the data URL to get the base64 part
        try:
            header, base64_data = data_url.split(",", 1)
            print(f"Header: {header}")
            print(f"Base64 data length: {len(base64_data)} chars")
            
            # Decode base64
            img_data = base64.b64decode(base64_data)
            print(f"Decoded image data: {len(img_data)} bytes")
            
        except Exception as e:
            print(f"Failed to decode base64: {e}")
            return jsonify({"error": f"Failed to decode image: {str(e)}"}), 500
        
        # Save image to disk
        img_id = str(uuid.uuid4().hex)
        filename = f"{img_id}.png"
        filepath = os.path.join(IMAGES_DIR, filename)
        
        with open(filepath, "wb") as f:
            f.write(img_data)
        print(f"Image saved to {filepath}")
        
        # Get image dimensions
        try:
            img = Image.open(io.BytesIO(img_data))
            width, height = img.size
            print(f"Image dimensions: {width}x{height}")
        except Exception as img_err:
            print(f"Could not read image dimensions: {img_err}")
            width, height = 1024, 1024
        
        # Create thumbnail
        thumbnail_base64 = None
        try:
            thumbnail_base64 = create_thumbnail(img_data)
            print(f"Created thumbnail ({len(thumbnail_base64) if thumbnail_base64 else 0} chars)")
        except Exception as thumb_err:
            print(f"Thumbnail creation failed: {thumb_err}")
        
        # Save to user history
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        users = load_users()
        user_data = get_user_data_with_sessions(session["gmail"])
        active_session_id = user_data.get("active_session")
        
        if active_session_id:
            active_session = user_data["sessions"][active_session_id]
            
            image_entry = {
                "sender": "bot",
                "type": "image",
                "content": f"[IMAGE:{img_id}]",
                "image_id": img_id,
                "filename": filename,
                "prompt": prompt,
                "time": timestamp,
                "image_info": {
                    "width": width,
                    "height": height,
                    "size_kb": round(len(img_data) / 1024, 2),
                    "thumbnail": thumbnail_base64
                }
            }
            
            active_session["history"].append(image_entry)
            users[session["gmail"]] = user_data
            save_users(users)
        
        return jsonify({
            "success": True,
            "url": f"/images/{filename}",
            "id": img_id,
            "dimensions": f"{width}x{height}",
            "size_kb": round(len(img_data) / 1024, 2),
            "thumbnail": thumbnail_base64
        })

    except requests.exceptions.RequestException as e:
        print(f"OpenRouter API request failed: {type(e).__name__}: {str(e)}")
        return jsonify({"error": f"API request failed: {str(e)}"}), 500
    except Exception as e:
        print(f"Image generation error: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Image processing failed: {str(e)}"}), 500

@app.route("/image-debug", methods=["POST"])
def image_gen_debug():
    """Debug endpoint to see what OpenRouter returns"""
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    prompt = request.json.get("prompt", "a cute cat").strip()
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "google/gemini-2.5-flash-image-preview",
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["image", "text"]
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        
        # Return structured info
        debug_info = {
            "status": "success",
            "has_choices": "choices" in data and len(data["choices"]) > 0,
        }
        
        if debug_info["has_choices"]:
            message = data["choices"][0]["message"]
            debug_info["has_images"] = "images" in message and len(message["images"]) > 0
            
            if debug_info["has_images"]:
                first_image = message["images"][0]
                debug_info["image_structure"] = {
                    "type": type(first_image).__name__,
                    "keys": list(first_image.keys()) if isinstance(first_image, dict) else "N/A"
                }
                
                if isinstance(first_image, dict) and "image_url" in first_image:
                    image_url = first_image["image_url"]
                    debug_info["image_url_structure"] = {
                        "type": type(image_url).__name__,
                        "keys": list(image_url.keys()) if isinstance(image_url, dict) else "N/A"
                    }
                    
                    if isinstance(image_url, dict) and "url" in image_url:
                        url_value = image_url["url"]
                        debug_info["url_info"] = {
                            "is_data_url": url_value.startswith("data:image/") if isinstance(url_value, str) else False,
                            "url_preview": str(url_value)[:100] + "..." if isinstance(url_value, str) and len(url_value) > 100 else str(url_value)
                        }
        
        return jsonify(debug_info)

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route("/test-image", methods=["GET"])
def test_image():
    """Test endpoint to see OpenRouter response format"""
    test_prompt = "a cute cat"
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "google/gemini-2.5-flash-image-preview",
        "messages": [{"role": "user", "content": test_prompt}],
        "modalities": ["image", "text"]
    }
    
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        
        # Save response for inspection
        with open("openrouter_response.json", "w") as f:
            json.dump(data, f, indent=2)
        
        # Return just the structure (not the full base64)
        if "choices" in data and len(data["choices"]) > 0:
            choice = data["choices"][0]
            if "message" in choice:
                message = choice["message"]
                
                # Create a safe copy without large base64
                safe_message = {}
                for key, value in message.items():
                    if key == "content" and isinstance(value, str):
                        # Truncate base64 data
                        if "base64" in value.lower():
                            safe_message[key] = value[:200] + "... [TRUNCATED]"
                        else:
                            safe_message[key] = value[:500] + "..."
                    elif key == "images":
                        safe_message[key] = f"Array with {len(value)} items"
                    else:
                        safe_message[key] = str(value)[:200] + "..." if isinstance(value, str) else value
                
                return jsonify({
                    "status": "success",
                    "response_structure": safe_message,
                    "saved_to": "openrouter_response.json"
                })
        
        return jsonify({"status": "success", "data": data})
    
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@app.route("/image/thumbnail/<image_id>")
def get_image_thumbnail(image_id):
    """Get thumbnail for an image"""
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    users = load_users()
    user_data = users.get(session["gmail"], {})
    
    # Check if image exists in user's data
    if "images" in user_data and image_id in user_data["images"]:
        thumbnail = user_data["images"][image_id].get("thumbnail")
        if thumbnail:
            # Return as data URL
            return jsonify({
                "thumbnail": f"data:image/jpeg;base64,{thumbnail}",
                "image_id": image_id
            })
    
    return jsonify({"error": "Thumbnail not found"}), 404


@app.route("/user/images")
def get_user_images():
    """Get all images for current user"""
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    users = load_users()
    user_data = users.get(session["gmail"], {})
    
    images = user_data.get("images", {})
    
    # Return only metadata (not thumbnails) for list view
    image_list = []
    for img_id, img_data in images.items():
        image_list.append({
            "id": img_id,
            "filename": img_data.get("filename"),
            "prompt": img_data.get("prompt", ""),
            "created": img_data.get("created"),
            "dimensions": img_data.get("dimensions", "Unknown"),
            "size_kb": img_data.get("size_kb", 0),
            "url": f"/images/{img_data.get('filename')}"
        })
    
    return jsonify({"images": image_list})





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