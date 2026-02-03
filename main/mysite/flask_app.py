# =============================================================================
# HurairahGPT - Flask Backend Application
# =============================================================================
# Copyright (c) 2025 Hurairah
# All Rights Reserved. Proprietary Software.
# Legal matters handled by parent/guardian until age 18.
# Governed by Pakistan law (Rawalpindi jurisdiction).
#
# Description:
#     This is the main Flask application for HurairahGPT, an AI-powered chat
#     application with image generation capabilities. The application provides
#     user authentication, chat session management, AI-powered conversations,
#     image generation with tier-based limits, and theming support.
#
# Dependencies:
#     - Flask: Web framework for serving the application
#     - OpenAI: AI chat completions and image generation
#     - PIL: Image processing and thumbnail generation
#     - Various utility libraries for email, HTTP requests, etc.
#
# Author: Hurairah (Solo Developer)
# Email: hurairahgpt.devteam@gmail.com
# Website: talktohurairah.com
# =============================================================================

# Standard Library Imports
import re
import uuid
import traceback
import json
import os
import time
import base64
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable

# Import migration system modules
from database import init_db, get_stats, user_exists, get_user_by_email
from migration import MigrationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Third-Party Library Imports
from flask import (
    Flask, render_template, request, redirect, session, url_for,
    jsonify, Response, stream_with_context, send_from_directory
)
from openai import OpenAI
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PIL import Image
import io

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()



# =============================================================================
# Application Configuration
# =============================================================================

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default-secret-key-change-in-production")

# Directory Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
IMAGES_DIR = os.path.join(BASE_DIR, "user_images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# =============================================================================
# User Tier System Configuration
# =============================================================================
# The user tier system provides different levels of image generation quotas.
# Each tier has specific limits and pricing information.
#
# Tiers:
#     - free: Basic tier with limited image generation (2 images per 8 hours)
#     - premium: Enhanced tier with more generous limits (10 images per 8 hours)
#     - unlimited: Premium tier with very high limits (100 images per 8 hours)
# =============================================================================

USER_TIERS: Dict[str, Dict[str, Any]] = {
    "free": {
        "images_per_8hrs": 2,
        "name": "Free",
        "price": "$0",
        "description": "Basic access with limited image generation"
    },
    "premium": {
        "images_per_8hrs": 10,
        "name": "Premium",
        "price": "$9.99/month",
        "description": "Enhanced access with higher image generation limits"
    },
    "unlimited": {
        "images_per_8hrs": 100,
        "name": "Unlimited",
        "price": "$19.99/month",
        "description": "Maximum access with generous image generation quotas"
    }
}

# Initialize users.json if it doesn't exist
def initialize_users_file() -> None:
    """
    Initialize the users.json file if it doesn't exist.
    
    This function ensures that the users data file is created with an
    empty dictionary if it doesn't already exist.
    
    Side Effects:
        Creates the users.json file if it doesn't exist
    """
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)

initialize_users_file()

# =============================================================================
# Database Migration System
# =============================================================================
# Initialize the database and run automatic migration on startup
# This ensures all file-based data is migrated to SQLite

def initialize_database_and_migration() -> None:
    """
    Initialize the database and run automatic migration.
    
    This function:
    1. Initializes the SQLite database schema
    2. Runs automatic migration of file-based data
    3. Logs migration results
    
    Side Effects:
        - Creates the database file if it doesn't exist
        - Migrates data from credentials.txt, users.json, rate_limits.json
    """
    try:
        # Initialize database schema
        init_db()
        logger.info("Database initialized successfully")
        
        # Run automatic migration
        logger.info("Starting automatic data migration...")
        migration_manager = MigrationManager()
        report = migration_manager.run_auto_migration()
        
        # Log migration results
        if report.total_records_migrated > 0:
            logger.info(
                f"Migration completed: {report.total_records_migrated} records "
                f"migrated from {report.total_files_migrated} files"
            )
        else:
            logger.info("No new data to migrate (files unchanged since last migration)")
        
        # Log any errors
        if report.total_errors > 0:
            logger.warning(f"Migration completed with {report.total_errors} errors")
        
        # Log database stats
        stats = get_stats()
        logger.info(f"Database stats: {stats['user_count']} users, "
                   f"{stats['session_count']} sessions, "
                   f"{stats['message_count']} messages")
        
    except Exception as e:
        logger.error(f"Database/migration initialization failed: {e}")
        # Continue without failing - file-based storage will be used as fallback
        logger.warning("Application will continue with file-based storage as fallback")

# Run database initialization and migration
initialize_database_and_migration()

# Mobile User-Agent Detection Regex
# Used to detect mobile devices for responsive template rendering
MOBILE_UA_RE = re.compile(
    r"android|iphone|ipad|ipod|blackberry|iemobile|windows phone|opera mini|mobile",
    re.I
)

# =============================================================================
# AI Client Configuration
# =============================================================================
# Configure the OpenAI client for AI chat completions and image generation.
# Uses OpenRouter as the API gateway for accessing various AI models.
# =============================================================================

openai_client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
)

# AI Model Configuration
CHAT_MODEL: str = "nvidia/nemotron-3-nano-30b-a3b:free"
IMAGE_MODEL: str = "bytedance-seed/seedream-4.5"

# =============================================================================
# AI Personality System Configuration
# =============================================================================
# Defines different AI personalities that users can select for their chat
# experience. Each personality has a unique system prompt that shapes the
# AI's responses and behavior.
# =============================================================================

AI_PERSONALITIES: Dict[str, str] = {
    "default": "You are a helpful AI assistant. You are friendly, professional, and always strive to provide accurate and useful information to the user. You respond concisely but thoroughly when needed.",
    "funny": "You are sarcastic, witty, and always crack jokes. You have a great sense of humor and love to make the user laugh. You use clever wordplay and lighthearted responses while still being helpful.",
    "islamic": "You answer with Islamic knowledge, Quran, and Hadith (avoid opinions). You provide scholarly responses based on authentic Islamic sources. You are respectful and careful to distinguish between established knowledge and scholarly opinions.",
    "coder": "You are a senior programmer. Answer with code first, minimal talk. You provide clean, well-documented code examples. You explain technical concepts clearly and suggest best practices. You are proficient in multiple programming languages and frameworks."
}


def load_users_from_file() -> Dict[str, Dict[str, Any]]:
    """
    Load all user data from the users.json file.
    
    This function reads the persisted user data from the JSON file and
    returns it as a dictionary. If the file doesn't exist or contains
    invalid JSON, an empty dictionary is returned.
    
    Returns:
        Dict containing all user data, keyed by email address
    
    Raises:
        FileNotFoundError: If the users file doesn't exist (returns empty dict)
        JSONDecodeError: If the file contains invalid JSON (returns empty dict)
    """
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load users file: {e}")
        return {}


def save_users_to_file(users: Dict[str, Dict[str, Any]]) -> bool:
    """
    Save all user data to the users.json file.
    
    This function persists the complete user data dictionary to the JSON
    file with pretty printing for human readability.
    
    Args:
        users: Dictionary containing all user data to save
    
    Returns:
        bool: True if save was successful, False otherwise
    
    Side Effects:
        Overwrites the users.json file with new data
    """
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        return True
    except (IOError, TypeError) as e:
        print(f"Error saving users file: {e}")
        return False


# Alias functions for backward compatibility
def load_users() -> Dict[str, Dict[str, Any]]:
    """Alias for load_users_from_file() for backward compatibility."""
    return load_users_from_file()


def save_users(users: Dict[str, Dict[str, Any]]) -> bool:
    """Alias for save_users_to_file() for backward compatibility."""
    return save_users_to_file(users)


def migrate_user_data_to_sessions_structure(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate legacy user data to the new sessions-based structure.
    
    This function handles the migration of user data from older versions
    that stored chat history directly in the user object to the new
    sessions-based structure that supports multiple chat sessions.
    
    The migration process:
    1. Checks if user already has sessions structure
    2. If not, creates a default session with existing history
    3. Preserves all existing chat history
    4. Removes the legacy "history" field
    
    Args:
        user_data: The user data dictionary to migrate
    
    Returns:
        Updated user data with sessions structure
    
    Example:
        >>> old_data = {"history": [{"sender": "user", "content": "Hello"}]}
        >>> migrated = migrate_user_data_to_sessions_structure(old_data)
        >>> "sessions" in migrated
        True
    """
    if "sessions" in user_data:
        return user_data  # Already migrated to new structure

    # Create unique session ID for the migrated session
    session_id = str(uuid.uuid4())
    old_history = user_data.get("history", [])

    # Create new sessions structure with migrated history
    user_data["sessions"] = {
        session_id: {
            "name": "Chat 1",
            "history": old_history,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    user_data["active_session"] = session_id

    # Remove legacy history field
    if "history" in user_data:
        del user_data["history"]

    return user_data


def migrate_user_to_tier_system(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate legacy user data to the new tier-based subscription system.
    
    This function ensures that all users have the required tier-related
    fields. It migrates from older data structures that may have had
    different premium status indicators.
    
    The migration process:
    1. Adds tier information if missing
    2. Migrates legacy "premium" boolean field to tier system
    3. Preserves any existing image count data
    4. Initializes image usage tracking
    
    Args:
        user_data: The user data dictionary to migrate
    
    Returns:
        Updated user data with tier system fields
    
    Example:
        >>> old_data = {"premium": True, "image_count": 5}
        >>> migrated = migrate_user_to_tier_system(old_data)
        >>> migrated["tier"]
        'premium'
    """
    # Default tier structure for new users
    tier_structure = {
        "tier": "free",
        "image_usage": {
            "last_reset": datetime.now().isoformat(),
            "count": 0
        },
        "upgrade_history": []
    }
    
    # Check if user already has tier data
    if "tier" not in user_data:
        # Migrate existing image count if any
        if "image_count" in user_data:
            tier_structure["image_usage"]["count"] = user_data.get("image_count", 0)
            del user_data["image_count"]
        
        # Apply default tier structure
        user_data.update(tier_structure)
        
        # Check if user has premium features (migrate from legacy premium field)
        if user_data.get("premium", False):
            user_data["tier"] = "premium"
    
    return user_data


def get_user_data_with_sessions(gmail: str) -> Dict[str, Any]:
    """
    Retrieve complete user data with proper sessions structure.
    
    This function fetches user data from the database, ensuring that all
    required fields are present and properly migrated. It handles the
    creation of default sessions and applies necessary data migrations.
    
    The function performs the following operations:
    1. Loads all users from the database
    2. Gets or creates user data for the given email
    3. Applies sessions migration if needed
    4. Applies tier system migration if needed
    5. Ensures a valid active session exists
    6. Saves any changes to the database
    
    Args:
        gmail: The email address of the user to retrieve
    
    Returns:
        Complete user data dictionary with all required fields
    
    Raises:
        KeyError: If gmail parameter is None or empty (should be validated by caller)
    
    Example:
        >>> user_data = get_user_data_with_sessions("user@example.com")
        >>> user_data["sessions"]
        {'uuid-here': {'name': 'Chat 1', 'history': [], ...}}
    """
    users = load_users_from_file()
    
    # Default user structure for new users
    default_user_data = {
        "sessions": {},
        "active_session": None,
        "theme": "dark",
        "personality": "default",
        "tier": "free",
        "image_usage": {
            "last_reset": datetime.now().isoformat(),
            "count": 0
        },
        "upgrade_history": []
    }
    
    user_data = users.get(gmail, default_user_data)

    # Apply migrations
    user_data = migrate_user_data_to_sessions_structure(user_data)
    user_data = migrate_user_to_tier_system(user_data)

    # Ensure active_session is valid
    if not user_data.get("active_session") or user_data["active_session"] not in user_data.get("sessions", {}):
        if not user_data.get("sessions"):
            # Create first session for new users
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

    # Save updated user data
    users[gmail] = user_data
    save_users_to_file(users)

    return user_data


def get_active_session_history(user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Retrieve the chat history from the user's active session.
    
    This function extracts and returns the message history from whichever
    session is currently marked as active for the user.
    
    Args:
        user_data: The complete user data dictionary
    
    Returns:
        List of message dictionaries from the active session.
        Each message has "content", "sender", and "time" fields.
        Returns empty list if no active session exists.
    
    Example:
        >>> history = get_active_session_history(user_data)
        >>> len(history)
        5
        >>> history[0]["sender"]
        'user'
    """
    active_session_id = user_data.get("active_session")
    if not active_session_id:
        return []
    
    sessions = user_data.get("sessions", {})
    active_session = sessions.get(active_session_id, {})
    return active_session.get("history", [])


def check_image_generation_allowance(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if a user can generate an image based on their tier and usage.
    
    This function evaluates whether the user has remaining image generation
    quota within their current 8-hour window. It considers:
    - User's subscription tier (free, premium, unlimited)
    - Current usage within the 8-hour window
    - Whether the 8-hour window has expired
    
    Args:
        user_data: The complete user data dictionary
    
    Returns:
        Dictionary containing:
        - allowed (bool): Whether user can generate an image
        - remaining (int): Number of images remaining in current window
        - next_reset (datetime): When the 8-hour window resets
        - reset_seconds (int): Seconds until next reset
        - tier (str): User's current tier
    
    Example:
        >>> result = check_image_generation_allowance(user_data)
        >>> result["allowed"]
        True
    """
    tier = user_data.get("tier", "free")
    image_usage = user_data.get("image_usage", {})
    
    # Get user's image generation limit based on tier
    tier_config = USER_TIERS.get(tier, USER_TIERS["free"])
    limit = tier_config["images_per_8hrs"]
    
    # Check if 8-hour reset period has passed
    last_reset_str = image_usage.get("last_reset")
    if last_reset_str:
        try:
            last_reset = datetime.fromisoformat(last_reset_str)
            time_since_reset = datetime.now() - last_reset
            eight_hours_seconds = 8 * 3600
            
            # Reset if 8 hours have passed
            if time_since_reset.total_seconds() >= eight_hours_seconds:
                return {
                    "allowed": True,
                    "remaining": limit,
                    "next_reset": datetime.now() + timedelta(hours=8),
                    "reset_seconds": eight_hours_seconds,
                    "tier": tier
                }
        except (ValueError, TypeError):
            # Invalid timestamp format, proceed with normal check
            pass
    
    # Calculate current usage and remaining quota
    current_count = image_usage.get("count", 0)
    remaining = max(0, limit - current_count)
    
    # Calculate next reset time
    last_reset = datetime.fromisoformat(last_reset_str) if last_reset_str else datetime.now()
    next_reset = last_reset + timedelta(hours=8)
    reset_seconds = max(0, int((next_reset - datetime.now()).total_seconds()))
    
    return {
        "allowed": current_count < limit,
        "remaining": remaining,
        "next_reset": next_reset,
        "reset_seconds": reset_seconds,
        "tier": tier
    }


def increment_image_usage_counter(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Increment the user's image generation counter and manage reset logic.
    
    This function updates the image usage counter, checking if the 8-hour
    window has expired and should be reset. It ensures accurate tracking
    of image generation usage.
    
    Args:
        user_data: The complete user data dictionary
    
    Returns:
        Updated user data dictionary with incremented image count
    
    Side Effects:
        Modifies the image_usage field in user_data
    """
    image_usage = user_data.get("image_usage", {})
    
    # Check if we need to reset the counter
    last_reset_str = image_usage.get("last_reset")
    eight_hours_seconds = 8 * 3600
    
    if last_reset_str:
        try:
            last_reset = datetime.fromisoformat(last_reset_str)
            time_since_reset = datetime.now() - last_reset
            
            # Reset if 8 hours have passed
            if time_since_reset.total_seconds() >= eight_hours_seconds:
                image_usage["count"] = 0
                image_usage["last_reset"] = datetime.now().isoformat()
        except (ValueError, TypeError):
            # Reset on error parsing timestamp
            image_usage["count"] = 0
            image_usage["last_reset"] = datetime.now().isoformat()
    else:
        # First time usage - initialize
        image_usage["last_reset"] = datetime.now().isoformat()
        image_usage["count"] = 0
    
    # Increment the counter
    image_usage["count"] = image_usage.get("count", 0) + 1
    user_data["image_usage"] = image_usage
    
    return user_data


def send_credential_email(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    """
    Send an email using SMTP with the provided parameters.
    
    This function sends emails for password reset and credential retrieval
    operations. It uses Gmail's SMTP server with TLS encryption.
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        body: Email body content (plain text)
    
    Returns:
        Tuple of (success: bool, message: str)
        On success, returns (True, "Email sent successfully.")
        On failure, returns (False, error_description: str)
    
    Prerequisites:
        SMTP_EMAIL and SMTP_PASSWORD environment variables must be set
    
    Side Effects:
        - Connects to Gmail's SMTP server
        - Sends an email message
        - Properly closes SMTP connection
    """
    sender_email = os.getenv("SMTP_EMAIL")
    sender_password = os.getenv("SMTP_PASSWORD")

    if not sender_email or not sender_password:
        return False, "Email configuration missing"

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
    except smtplib.SMTPAuthenticationError:
        return False, "Email authentication failed"
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def find_user_credentials(email_to_find: str) -> Optional[str]:
    """
    Find user credentials by email address from credentials file.
    
    This function searches the credentials.txt file for a matching email
    and returns the associated password. The file supports multiple
    delimiter formats (colon, comma, space, tab).
    
    Args:
        email_to_find: Email address to search for (case-insensitive)
    
    Returns:
        The password string if found, None otherwise
    
    File Format:
        Each line should contain email and password separated by a delimiter.
        Lines starting with # are treated as comments and ignored.
    
    Example:
        >>> find_user_credentials("user@example.com")
        'password123'
    """
    credentials_path = Path(BASE_DIR) / "credentials.txt"
    credentials_path.touch(exist_ok=True)
    
    try:
        text = credentials_path.read_text(encoding="utf-8", errors="ignore")
    except IOError as e:
        print(f"Error reading credentials file: {e}")
        return None
    
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        
        # Try different delimiters
        for sep in [":", ",", " ", "\t"]:
            if sep in line:
                parts = [p.strip() for p in line.split(sep, 1)]
                if len(parts) >= 2 and parts[0].lower() == email_to_find.lower():
                    return parts[1]
    
    return None


def retry_api_request(
    func: Callable[[], Any],
    max_retries: int = 3,
    retry_delay: float = 1.0,
    fallback_value: Any = "Unavailable"
) -> Any:
    """
    Retry a function call with exponential backoff on failure.
    
    This utility function is useful for API calls that may fail transiently
    due to network issues or rate limiting. It attempts the function
    multiple times with delays between attempts.
    
    Args:
        func: Callable function to execute
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Delay between retries in seconds (default: 1.0)
        fallback_value: Value to return if all retries fail
    
    Returns:
        Result of func() if successful, fallback_value otherwise
    
    Side Effects:
        - Sleeps between retry attempts
        - Logs errors with full traceback on final failure
    
    Example:
        >>> result = retry_api_request(lambda: api_call(), retries=3)
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                # Exponential backoff
                time.sleep(retry_delay * (2 ** attempt))
            else:
                # Log the error on the last attempt with full traceback
                print(f"Error after {max_retries} attempts: {type(e).__name__}: {str(e)}")
                print(f"Traceback: {traceback.format_exc()}")
    
    return fallback_value


def get_application_context() -> str:
    """
    Get the application context for AI system prompts.
    
    This function provides contextual information about the application
    that should be included in AI system prompts. It ensures the AI
    understands its role and the application's identity.
    
    Returns:
        String containing application context information
    """
    return (
        "You are in an app called HurairahGPT. "
        "The website is talktohurairah.com. "
        "You were developed by Hurairah, who is a solo developer building and maintaining this project. "
        "You can contact the team at hurairahgpt.devteam@gmail.com. "
        "Hurairah is a male developer passionate about AI technology."
    )


def get_natural_conversation_instructions() -> str:
    """
    Get instructions for natural conversation behavior.
    
    This function provides guidelines for the AI to behave naturally
    in conversations, avoiding overly formal system-like responses.
    
    Returns:
        String containing natural conversation instructions
    """
    return (
        "You should act natural in your responses. "
        "Don't use system-prompt-like language for time, date, or data. "
        "Respond naturally as if you're a real assistant. "
        "For example, if the user says hi, respond with hello and ask how you can help them."
    )

@app.route("/")
def render_main_page():
    """
    Render the main application page.
    
    This route serves as the main entry point for authenticated users.
    It detects whether the request is from a mobile device and serves
    the appropriate template. Unauthenticated users are redirected to
    login.
    
    Query Parameters:
        mobile: Force mobile view (1, true, yes)
        desktop: Force desktop view (1, true, yes)
    
    Returns:
        - Rendered HTML template for index.html (desktop)
        - Rendered HTML template for moindex.html (mobile)
        - Redirect to /login if not authenticated
    
    Template Context:
        - gmail: User's email address
        - history: Chat history from active session
        - theme: User's preferred theme (dark/light)
        - sessions: All user sessions
        - active_session: Currently active session ID
        - tier: User's subscription tier
        - tier_info: Tier configuration details
        - image_limits: Image generation allowance information
    """
    if "gmail" not in session:
        return redirect(url_for("render_login_page"))

    # Detect mobile device from User-Agent header
    user_agent = request.headers.get("User-Agent", "")
    is_mobile = bool(MOBILE_UA_RE.search(user_agent))

    # Allow query parameter override for mobile/desktop view
    if request.args.get("mobile") in ("1", "true", "yes"):
        is_mobile = True
    if request.args.get("desktop") in ("1", "true", "yes"):
        is_mobile = False

    # Retrieve user data and session information
    user_data = get_user_data_with_sessions(session["gmail"])
    history = get_active_session_history(user_data)
    sessions_list = user_data.get("sessions", {})
    active_session_id = user_data.get("active_session")
    
    # Get image generation limits info
    image_limits = check_image_generation_allowance(user_data)
    tier_info = USER_TIERS.get(user_data.get("tier", "free"), USER_TIERS["free"])

    # Select appropriate template based on device type
    if is_mobile:
        return render_template(
            "moindex.html",
            gmail=session["gmail"],
            history=history,
            theme=user_data["theme"],
            sessions=sessions_list,
            active_session=active_session_id,
            tier=user_data.get("tier", "free"),
            tier_info=tier_info,
            image_limits=image_limits
        )
    
    return render_template(
        "index.html",
        gmail=session["gmail"],
        history=history,
        theme=user_data["theme"],
        sessions=sessions_list,
        active_session=active_session_id,
        tier=user_data.get("tier", "free"),
        tier_info=tier_info,
        image_limits=image_limits
    )


@app.route("/robots.txt")
def serve_robots_file():
    """
    Serve the robots.txt file for search engine crawlers.
    
    Returns:
        The robots.txt file contents with appropriate MIME type
    """
    return send_from_directory(".", "robots.txt")


@app.route("/images/<filename>")
def serve_generated_image(filename: str):
    """
    Serve a user-generated image from the images directory.
    
    This route allows users to access images they have generated.
    Images are stored with UUID filenames for security and organization.
    
    Args:
        filename: The UUID filename of the image to serve
    
    Returns:
        Image file from the user_images directory
    """
    return send_from_directory(IMAGES_DIR, filename)


@app.route("/deletedata")
def render_data_deletion_page():
    """
    Render the data deletion information page.
    
    This page provides information about data deletion policies
    and processes for GDPR/compliance purposes.
    
    Returns:
        Rendered HTML template for deletedata.html
    """
    return render_template("deletedata.html")


@app.route("/slipt")
def render_split_page():
    """
    Render a placeholder split page.
    
    This route serves a utility page that may be used for
    testing or specific application features.
    
    Returns:
        Rendered HTML template for slipt.html
    """
    return render_template("slipt.html")


@app.route("/main")
def render_main_alt_page():
    """
    Alternative route for the main page (alias for root).
    
    This route provides an alternative entry point to the main
    application page. It serves the same content as the root route
    but through a different URL path.
    
    Returns:
        - Rendered HTML template for index.html
        - Redirect to /login if not authenticated
    """
    if "gmail" not in session:
        return redirect(url_for("render_login_page"))
    
    user_data = get_user_data_with_sessions(session["gmail"])
    history = get_active_session_history(user_data)
    sessions_list = user_data.get("sessions", {})
    active_session_id = user_data.get("active_session")
    
    # Get image generation limits info
    image_limits = check_image_generation_allowance(user_data)
    tier_info = USER_TIERS.get(user_data.get("tier", "free"), USER_TIERS["free"])
    
    return render_template(
        "index.html",
        gmail=session["gmail"],
        history=history,
        theme=user_data["theme"],
        sessions=sessions_list,
        active_session=active_session_id,
        tier=user_data.get("tier", "free"),
        tier_info=tier_info,
        image_limits=image_limits
    )


@app.route("/login", methods=["GET", "POST"])
def render_login_page():
    """
    Handle user authentication and login requests.
    
    GET: Render the login form template
    POST: Validate credentials and create authenticated session
    
    Form Parameters:
        gmail: User's email address
        password: User's password
    
    Returns:
        - GET: Rendered login.html template
        - POST (success): Redirect to main page
        - POST (error): Login page with error message
        
    Special Accounts:
        - guest@gmail.com / guest: Grants temporary guest access
    """
    if request.method == "POST":
        gmail = request.form.get("gmail", "").strip()
        password = request.form.get("password", "").strip()

        # Validate required fields
        if not gmail or not password:
            return render_template("login.html", error="Please fill out all fields.")

        # Handle guest account login
        if gmail.lower() == "guest@gmail.com" and password == "guest":
            session["gmail"] = "guest@gmail.com"
            users = load_users_from_file()
            
            if "guest@gmail.com" not in users:
                # Initialize guest user data
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
                    "personality": "default",
                    "tier": "free",
                    "image_usage": {
                        "last_reset": datetime.now().isoformat(),
                        "count": 0
                    },
                    "upgrade_history": []
                }
                save_users_to_file(users)
            
            return redirect(url_for("render_main_page"))

        # Regular account authentication
        stored_pw = find_user_credentials(gmail)
        
        if not stored_pw:
            return render_template("login.html", error="Account not found. Please sign up first.")

        if stored_pw != password:
            return render_template("login.html", error="Incorrect password.")

        # Successful login - create session
        session["gmail"] = gmail
        users = load_users_from_file()
        
        # Initialize user data if first login
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
                "personality": "default",
                "tier": "free",
                "image_usage": {
                    "last_reset": datetime.now().isoformat(),
                    "count": 0
                },
                "upgrade_history": []
            }
            save_users_to_file(users)
        
        return redirect(url_for("render_main_page"))

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def render_signup_page():
    """
    Handle user registration and account creation.
    
    GET: Render the signup form template
    POST: Create new user account with provided credentials
    
    Form Parameters:
        gmail: User's email address (must be unique)
        password: User's chosen password
    
    Returns:
        - GET: Rendered signup.html template
        - POST (success): Redirect to main page
        - POST (error): Signup page with error message
    
    Side Effects:
        - Creates new entry in credentials.txt
        - Creates new user data in users.json
        - Creates authenticated session
    """
    if request.method == "POST":
        gmail = request.form.get("gmail", "").strip()
        password = request.form.get("password", "").strip()

        # Validate required fields
        if not gmail or not password:
            return render_template("signup.html", error="Please fill out all fields.")

        # Validate email format
        if "@" not in gmail or "." not in gmail:
            return render_template("signup.html", error="Please enter a valid email address.")

        credentials_path = os.path.join(BASE_DIR, "credentials.txt")
        os.makedirs(os.path.dirname(credentials_path), exist_ok=True)

        # Check if the user already exists
        existing_pw = find_user_credentials(gmail)
        if existing_pw:
            return render_template("signup.html", error="Account already exists. Please log in.")

        # Register the new account in credentials file
        with open(credentials_path, "a", encoding="utf-8") as f:
            f.write(f"{gmail}:{password}\n")

        # Add new user record with sessions structure
        users = load_users_from_file()
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
            "personality": "default",
            "tier": "free",
            "image_usage": {
                "last_reset": datetime.now().isoformat(),
                "count": 0
            },
            "upgrade_history": []
        }
        save_users_to_file(users)

        session["gmail"] = gmail
        return redirect(url_for("render_main_page"))

    return render_template("signup.html")


@app.route("/logout")
def handle_logout():
    """
    Log out the current user and clear their session.
    
    This route removes the user's email from the session and
    redirects them to the login page.
    
    Returns:
        Redirect response to the login page
    
    Side Effects:
        - Clears 'gmail' key from session
    """
    session.pop("gmail", None)
    return redirect(url_for("render_login_page"))


@app.route("/chat", methods=["POST"])
def handle_chat_message():
    """
    Process incoming chat messages and generate AI responses.
    
    This is the main chat endpoint that handles user messages, maintains
    conversation context, and returns AI-generated responses. It supports
    both streaming and non-streaming response modes.
    
    Request JSON Body:
        message: The user's input message
        stream: Boolean to enable streaming response (optional, default: False)
    
    Returns:
        Non-streaming: JSON {"response": "AI reply text"}
        Streaming: Server-Sent Events (SSE) with chunks
        Error: JSON {"error": "error message"} with HTTP status code
    
    HTTP Status Codes:
        200: Success
        400: Bad request (missing message or invalid session)
        401: Unauthorized (not logged in)
        500: AI service error
    
    Special Commands:
        "__CLEAR__": Clears the chat history for current session
    
    Side Effects:
        - Saves chat history to users.json
        - Updates session activity timestamp
    """
    # Verify user authentication
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_message = request.json.get("message", "")
    
    # Validate message presence
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Load user data
    users = load_users_from_file()
    user_data = get_user_data_with_sessions(session["gmail"])
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Validate active session
    active_session_id = user_data.get("active_session")
    if not active_session_id or active_session_id not in user_data.get("sessions", {}):
        return jsonify({"error": "No active session"}), 400

    active_session = user_data["sessions"][active_session_id]
    history = active_session.get("history", [])

    # Handle chat history clearing command
    if user_message == "__CLEAR__":
        active_session["history"] = []
        users[session["gmail"]] = user_data
        save_users_to_file(users)
        return jsonify({"response": "Chat history cleared."})

    # Check if streaming is requested
    stream_response = request.json.get("stream", False)

    # Build system prompt with personality and context
    user_personality = user_data.get("personality", "default")
    system_content = AI_PERSONALITIES.get(user_personality, AI_PERSONALITIES["default"]) + "\n\n" + "\n".join([
        f"Today is {datetime.now().strftime('%A, %B %d, %Y')}.",
        get_application_context(),
        get_natural_conversation_instructions()
    ])

    # Construct message history for AI
    messages = [{"role": "system", "content": system_content}]
    for entry in history:
        role = "user" if entry["sender"] == "user" else "assistant"
        messages.append({"role": role, "content": entry["content"]})
    messages.append({"role": "user", "content": user_message})

    # Save user message immediately to history
    history.append({"content": user_message, "sender": "user", "time": timestamp})

    # Handle streaming response
    if stream_response:
        def generate_streaming_response():
            """Generate streaming response using Server-Sent Events"""
            full_response = ""
            try:
                stream_response_data = openai_client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=messages,
                    stream=True,
                    timeout=60
                )

                for chunk in stream_response_data:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content:
                            content = delta.content
                            full_response += content
                            # Send each chunk as SSE
                            yield f"data: {json.dumps({'chunk': content, 'done': False})}\n\n"

                # Send completion signal with full response
                yield f"data: {json.dumps({'chunk': '', 'done': True, 'full_response': full_response})}\n\n"

                # Save the full response to history
                history.append({"content": full_response, "sender": "bot", "time": timestamp})
                
                # Maintain reasonable history size (max 400 messages)
                if len(history) > 400:
                    active_session["history"] = history[-400:]
                else:
                    active_session["history"] = history

                users[session["gmail"]] = user_data
                save_users_to_file(users)

            except Exception as e:
                error_msg = "AI service unavailable, please try again later."
                print(f"Streaming API Error: {type(e).__name__}: {str(e)}")
                yield f"data: {json.dumps({'chunk': '', 'done': True, 'error': error_msg})}\n\n"
                
                # Save error message to history
                history.append({"content": error_msg, "sender": "bot", "time": timestamp})
                active_session["history"] = history
                users[session["gmail"]] = user_data
                save_users_to_file(users)
        
        return Response(
            stream_with_context(generate_streaming_response()),
            mimetype='text/event-stream'
        )
    
    # Non-streaming response (backward compatibility)
    def call_ai_api():
        """Call AI API and return response content"""
        try:
            response = openai_client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages,
                timeout=30
            )
            if not response.choices or len(response.choices) == 0:
                raise Exception("No response choices returned from API")
            return response.choices[0].message.content
        except Exception as e:
            error_msg = f"API Error: {type(e).__name__}: {str(e)}"
            print(error_msg)
            print(f"Model: {CHAT_MODEL}, Base URL: {openai_client.base_url}")
            raise

    # Retry API call with fallback
    ai_reply = retry_api_request(
        call_ai_api, 
        max_retries=2, 
        retry_delay=2, 
        fallback_value="AI service unavailable, please try again later."
    )

    if ai_reply == "AI service unavailable, please try again later.":
        print("Failed to get AI response after retries.")
        print("Please check:")
        print(f"  1. API key is valid: {openai_client.api_key[:20]}...")
        print(f"  2. Model name is correct: {CHAT_MODEL}")
        print(f"  3. Network connection to {openai_client.base_url}")
        print("  4. OpenRouter API status")

    # Save AI response to history
    history.append({"content": ai_reply, "sender": "bot", "time": timestamp})
    
    # Maintain reasonable history size
    if len(history) > 400:
        active_session["history"] = history[-400:]
    else:
        active_session["history"] = history

    users[session["gmail"]] = user_data
    save_users_to_file(users)

    return jsonify({"response": ai_reply})


def create_image_thumbnail(img_data: bytes, max_size: tuple[int, int] = (150, 150)) -> Optional[str]:
    """
    Create a base64-encoded thumbnail from image data.
    
    This function processes image bytes and creates a smaller thumbnail
    version for efficient display in chat interfaces. The thumbnail
    is converted to JPEG format and base64-encoded.
    
    Args:
        img_data: Raw image bytes
        max_size: Maximum width and height for thumbnail (default: 150x150)
    
    Returns:
        Base64-encoded JPEG string, or None if creation failed
    
    Image Processing:
        - Converts transparency to white background
        - Resizes maintaining aspect ratio
        - Optimizes for web display
    """
    try:
        # Open image from bytes
        img = Image.open(io.BytesIO(img_data))
        
        # Convert to RGB if necessary (handle transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
        
        # Create thumbnail with Lanczos resampling for quality
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert to optimized JPEG
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85, optimize=True)
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return img_str
    except Exception as e:
        print(f"Thumbnail creation failed: {e}")
        return None


@app.route("/image/check-limit")
def check_image_generation_limit():
    """
    Check the user's current image generation limits.
    
    This endpoint returns information about the user's remaining
    image generation quota within their current 8-hour window.
    
    Returns:
        JSON with limit information:
        {
            "allowed": bool,
            "remaining": int,
            "next_reset": datetime,
            "reset_seconds": int,
            "tier": str
        }
        
    HTTP Status Codes:
        200: Success
        401: Unauthorized (not logged in)
    """
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    users = load_users_from_file()
    user_data = users.get(session["gmail"], {})
    
    # Ensure user has tier data
    user_data = migrate_user_to_tier_system(user_data)
    
    # Check limits
    limit_info = check_image_generation_allowance(user_data)
    
    # Update user data if needed
    users[session["gmail"]] = user_data
    save_users_to_file(users)
    
    return jsonify(limit_info)


@app.route("/image", methods=["POST"])
def generate_image():
    """
    Generate an image based on the provided text prompt.
    
    This endpoint uses AI to generate images from text descriptions.
    It enforces tier-based usage limits and manages image storage.
    
    Request JSON Body:
        prompt: Text description of the image to generate
    
    Returns:
        JSON with image information:
        {
            "success": bool,
            "url": str,
            "id": str,
            "dimensions": str,
            "size_kb": float,
            "thumbnail": str,
            "limits": {...}
        }
        
    HTTP Status Codes:
        200: Success
        400: Bad request (missing prompt)
        401: Unauthorized
        429: Rate limit exceeded
        500: Generation failed
    
    Side Effects:
        - Saves generated image to disk
        - Increments user's image usage counter
        - Updates user's chat history
    """
    # Verify authentication
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    prompt = request.json.get("prompt", "").strip()
    
    # Validate prompt
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    if len(prompt) < 3:
        return jsonify({"error": "Prompt is too short (minimum 3 characters)"}), 400

    # Check image generation limits
    users = load_users_from_file()
    user_data = get_user_data_with_sessions(session["gmail"])
    
    # Check if user can generate image
    limit_check = check_image_generation_allowance(user_data)
    if not limit_check["allowed"]:
        return jsonify({
            "error": "Image limit reached. To upgrade your account, visit www.talktohurairah.com/upgrade. If you do not want to upgrade, your limit will reset in 8 hours.",
            "message": f"You have reached your {user_data['tier']} tier limit of {USER_TIERS[user_data['tier']]['images_per_8hrs']} images per 8 hours.",
            "next_reset": limit_check["next_reset"].isoformat(),
            "remaining_seconds": limit_check["reset_seconds"],
            "upgrade_url": "/upgrade"
        }), 429  # Too Many Requests


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
        
        # Increment image count for user
        user_data = increment_image_usage_counter(user_data)
        users[session["gmail"]] = user_data
        save_users_to_file(users)
        
        # Save to user history
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
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
        
        # Get updated limit info
        limit_info = check_image_generation_allowance(user_data)
        
        return jsonify({
            "success": True,
            "url": f"/images/{filename}",
            "id": img_id,
            "dimensions": f"{width}x{height}",
            "size_kb": round(len(img_data) / 1024, 2),
            "thumbnail": thumbnail_base64,
            "limits": {
                "remaining": limit_info["remaining"],
                "next_reset": limit_info["next_reset"].isoformat(),
                "tier": user_data["tier"]
            }
        })

    except requests.exceptions.RequestException as e:
        print(f"OpenRouter API request failed: {type(e).__name__}: {str(e)}")
        return jsonify({"error": f"API request failed: {str(e)}"}), 500
    except Exception as e:
        print(f"Image generation error: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Image processing failed: {str(e)}"}), 500


@app.route("/upgrade")
def upgrade_page():
    """Upgrade page to show tier options"""
    if "gmail" not in session:
        return redirect(url_for("login"))
    
    users = load_users_from_file()
    user_data = users.get(session["gmail"], {})
    user_data = migrate_user_to_tier_system(user_data)
    
    current_tier = user_data.get("tier", "free")
    limit_info = check_image_generation_allowance(user_data)
    
    return render_template("upgrade.html",
                          gmail=session["gmail"],
                          current_tier=current_tier,
                          user_tiers=USER_TIERS,
                          limit_info=limit_info)


@app.route("/upgrade/process", methods=["POST"])
def process_upgrade():
    """Process tier upgrade (simulated - no real payment)"""
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    new_tier = request.json.get("tier")
    if new_tier not in USER_TIERS:
        return jsonify({"error": "Invalid tier"}), 400
    
    users = load_users()
    user_data = users.get(session["gmail"], {})
    user_data = migrate_to_tier_system(user_data)
    
    current_tier = user_data.get("tier", "free")
    
    # Check if upgrading to same or lower tier
    if new_tier == current_tier:
        return jsonify({"error": "You are already on this tier"}), 400
    
    # In a real app, you would process payment here
    # For now, just update the tier
    
    # Record upgrade history
    upgrade_history = user_data.get("upgrade_history", [])
    upgrade_history.append({
        "from_tier": current_tier,
        "to_tier": new_tier,
        "timestamp": datetime.now().isoformat(),
        "price": USER_TIERS[new_tier]["price"]
    })
    
    # Update user tier
    user_data["tier"] = new_tier
    
    # Reset image count when upgrading
    user_data["image_usage"] = {
        "last_reset": datetime.now().isoformat(),
        "count": 0
    }
    
    # Save changes
    users[session["gmail"]] = user_data
    save_users_to_file(users)
    
    return jsonify({
        "success": True,
        "message": f"Upgraded to {USER_TIERS[new_tier]['name']} tier successfully!",
        "new_tier": new_tier,
        "tier_info": USER_TIERS[new_tier]
    })


@app.route("/user/profile")
def user_profile():
    """User profile page showing tier and usage"""
    if "gmail" not in session:
        return redirect(url_for("login"))
    
    users = load_users()
    user_data = users.get(session["gmail"], {})
    user_data = migrate_to_tier_system(user_data)
    
    limit_info = check_image_generation_allowance(user_data)
    current_tier = user_data.get("tier", "free")
    
    # Format next reset time nicely
    next_reset = limit_info.get("next_reset")
    if isinstance(next_reset, datetime):
        next_reset_str = next_reset.strftime("%Y-%m-%d %H:%M:%S")
    else:
        next_reset_str = str(next_reset)
    
    return jsonify({
        "email": session["gmail"],
        "tier": current_tier,
        "tier_name": USER_TIERS[current_tier]["name"],
        "images_used": user_data.get("image_usage", {}).get("count", 0),
        "images_limit": USER_TIERS[current_tier]["images_per_8hrs"],
        "images_remaining": limit_info["remaining"],
        "next_reset": next_reset_str,
        "upgrade_history": user_data.get("upgrade_history", [])
    })


@app.route("/theme", methods=["POST"])
def update_theme():
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    theme = request.json.get("theme")
    users = load_users_from_file()
    if session["gmail"] in users:
        users[session["gmail"]]["theme"] = theme
        save_users_to_file(users)
    return jsonify({"success": True})


@app.route("/personality", methods=["POST"])
def update_personality():
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    personality = request.json.get("personality", "default")
    users = load_users_from_file()
    if session["gmail"] in users:
        users[session["gmail"]]["personality"] = personality
        save_users_to_file(users)
    return jsonify({"success": True})


@app.route("/moindex")
def moindex():
    if "gmail" not in session:
        return redirect(url_for("login"))
    user_data = get_user_data_with_sessions(session["gmail"])
    history = get_active_session_history(user_data)
    sessions_list = user_data.get("sessions", {})
    active_session_id = user_data.get("active_session")
    
    # Get image generation limits info
    image_limits = check_image_generation_allowance(user_data)
    tier_info = USER_TIERS.get(user_data.get("tier", "free"), USER_TIERS["free"])
    
    return render_template("moindex.html",
                           gmail=session["gmail"],
                           history=history,
                           theme=user_data["theme"],
                           sessions=sessions_list,
                           active_session=active_session_id,
                           tier=user_data.get("tier", "free"),
                           tier_info=tier_info,
                           image_limits=image_limits)


@app.route("/forgot", methods=["GET"])
def forgot_get():
    return render_template("reset.html")


@app.route("/forgot", methods=["POST"])
def forgot_post():
    email = request.form.get("email", "").strip()
    if not email:
        return render_template("reset.html", error="Please enter your email.")

    users = load_users_from_file()
    password_found = None
    if email in users and users[email].get("password"):
        password_found = users[email]["password"]
    else:
        pw = find_user_credentials(email)
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
    data = request.json or {}
    session_name = data.get("name", "").strip() or f"Chat {len(user_data.get('sessions', {})) + 1}"

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
    save_users_to_file(users)

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
    save_users_to_file(users)

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


@app.route("/api/init", methods=["GET"])
def api_init():
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_data = get_user_data_with_sessions(session["gmail"])
    history = get_active_session_history(user_data)
    sessions_list = user_data.get("sessions", {})
    active_session_id = user_data.get("active_session")
    
    limit_info = check_image_generation_allowance(user_data)
    tier_info = USER_TIERS.get(user_data.get("tier", "free"), USER_TIERS["free"])
    
    return jsonify({
        "user": {
            "email": session["gmail"],
            "tier": user_data.get("tier", "free"),
            "theme": user_data.get("theme", "dark"),
            "personality": user_data.get("personality", "default")
        },
        "active_session_id": active_session_id,
        "sessions": sessions_list,
        "history": history,
        "limits": limit_info,
        "tier_info": tier_info
    })


@app.route("/api/generate_title", methods=["POST"])
def generate_title():
    if "gmail" not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    history = request.json.get("history", [])
    if not history:
         return jsonify({"title": "NEW"})
         
    # Extract first user message or a summary
    first_msg = next((h["content"] for h in history if h["sender"] == "user"), "")
    if not first_msg:
        return jsonify({"title": "CHT"})
        
    prompt = f"Summarize this text into exactly 3 uppercase letters that represent the topic. Do not include explanation. Text: {first_msg[:100]}"
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5
        )
        title = response.choices[0].message.content.strip().replace(".", "").upper()[:3]
        return jsonify({"title": title})
    except:
        return jsonify({"title": "CHT"})


# =============================================================================
# Migration System API Routes
# =============================================================================

@app.route("/api/migration/status", methods=["GET"])
def migration_status():
    """
    Get the current migration status and database statistics.
    
    Returns:
        JSON with migration status, database stats, and monitored files
    """
    try:
        from migration import MigrationManager
        from database import get_stats
        
        manager = MigrationManager()
        status = manager.get_migration_status()
        stats = get_stats()
        
        return jsonify({
            "success": True,
            "migration_status": status,
            "database_stats": stats
        })
    except Exception as e:
        logger.error(f"Error getting migration status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/migration/run", methods=["POST"])
def run_migration():
    """
    Manually trigger a data migration.
    
    Query Parameters:
        force: If true, force migration even if files haven't changed (default: false)
    
    Returns:
        JSON with migration results
    """
    try:
        force = request.args.get("force", "false").lower() == "true"
        
        logger.info(f"Manual migration triggered (force={force})")
        migration_manager = MigrationManager()
        report = migration_manager.run_auto_migration(force=force)
        
        return jsonify({
            "success": report.total_errors == 0,
            "message": f"Migration completed with {report.total_errors} errors",
            "results": {
                "files_scanned": report.total_files_scanned,
                "files_migrated": report.total_files_migrated,
                "records_migrated": report.total_records_migrated,
                "errors": report.total_errors,
                "warnings": report.total_warnings,
                "duration_seconds": report.duration_seconds
            }
        })
    except Exception as e:
        logger.error(f"Error running migration: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/migration/stats", methods=["GET"])
def migration_stats():
    """
    Get database statistics.
    
    Returns:
        JSON with counts of users, sessions, and messages
    """
    try:
        from database import get_stats
        
        stats = get_stats()
        return jsonify({
            "success": True,
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)