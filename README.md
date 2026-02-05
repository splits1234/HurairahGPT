# HurairahGPT Backend

![HurairahGPT](https://via.placeholder.com/400x100?text=HurairahGPT)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat-square&logo=flask)](https://flask.palletsprojects.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-API-412991?style=flat-square&logo=openai)](https://openai.com/)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running the Server](#running-the-server)
- [API Documentation](#api-documentation)
  - [Authentication Endpoints](#authentication-endpoints)
  - [Chat Endpoints](#chat-endpoints)
  - [Session Endpoints](#session-endpoints)
  - [Image Generation Endpoints](#image-generation-endpoints)
  - [User Management Endpoints](#user-management-endpoints)
- [Architecture](#architecture)
  - [Application Flow](#application-flow)
  - [Data Models](#data-models)
  - [Middleware](#middleware)
- [User Tier System](#user-tier-system)
- [Security](#security)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

---

## Overview

HurairahGPT Backend is a Flask-based web application that serves as the backend infrastructure for the HurairahGPT AI chatbot platform. It handles user authentication, chat session management, AI-powered conversations, image generation, and user preferences.

The backend integrates with OpenRouter's API to provide access to various AI models for both text generation and image creation.

---

## Features

### Core Features
- 🔐 **User Authentication** - Email/password-based authentication system
- 💬 **AI Chat** - Text-based conversations with multiple AI models
- 🖼️ **Image Generation** - AI-powered image creation from text prompts
- 👥 **Multi-Session Support** - Multiple chat sessions per user
- 🎨 **Theme Preferences** - Dark/light mode per user
- 🤖 **AI Personalities** - Configurable AI conversation styles
- 📊 **Usage Tracking** - Track image generation usage by tier
- 📱 **Mobile Support** - Responsive templates for mobile devices

### Technical Features
- 🔄 **Streaming Responses** - Real-time AI response streaming
- 🔁 **Session Persistence** - Chat history saved across sessions
- 📧 **Email Integration** - Password reset functionality
- 🛡️ **Rate Limiting** - API rate limiting (configurable)
- 📝 **Comprehensive Logging** - Error and access logging
- 🧪 **Input Validation** - Server-side input validation

---

## Project Structure

```
mysite/
├── templates/                    # HTML templates
│   ├── index.html               # Main chat interface
│   ├── moindex.html             # Mobile-optimized interface
│   ├── login.html               # Login page
│   ├── signup.html              # Registration page
│   ├── reset.html               # Password reset page
│   ├── upgrade.html             # Subscription upgrade page
│   ├── deletedata.html          # Data deletion info
│   ├── index_old.html           # Legacy template
│   └── slipt.html               # Utility template
├── static/                       # Static assets
│   ├── logo.png                 # Application logo
│   ├── logo-192.png             # PWA logo small
│   ├── manifest.json            # PWA manifest
│   ├── privacy.txt              # Privacy policy
│   ├── robots.txt               # Robots.txt
│   ├── service_worker.js        # PWA service worker
│   └── react_assets/            # Compiled React assets
├── user_images/                  # Generated images storage
├── flask_app.py                 # Main Flask application
├── users.json                   # User data storage
├── credentials.txt              # User credentials
├── rate_limits.json             # Rate limiting config
├── database.sqlite3            # SQLite database (if used)
├── .env                         # Environment variables
├── .gitignore
├── LICENSE
└── README.md                    # This file
```

---

## Getting Started

### Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **pip** - Python package manager
- **Virtual Environment** (recommended) - `python -m venv venv`
- **API Keys** - OpenRouter API key (for AI features)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/splits1234/hurairahgpt.git
   cd hurairahgpt/main/mysite
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # OR
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install flask flask-limiter openai python-dotenv pillow requests
   ```

### Configuration

Create a `.env` file in the mysite directory:

```env
# Flask Configuration
FLASK_SECRET_KEY=your-super-secret-key-change-in-production
FLASK_ENV=development  # Use 'production' for production

# OpenRouter API Configuration
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-api-key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# SMTP Configuration (for password reset)
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Image Generation (Optional - defaults provided)
IMG_MODEL=bytedance-seed/seedream-4.5

# Rate Limiting (requests per hour)
RATE_LIMIT=100
```

### Running the Server

**Development Mode:**
```bash
python flask_app.py
```

The server will start at `http://0.0.0.0:5000`

**Production Mode:**
```bash
# Set environment
export FLASK_ENV=production

# Run with production server
gunicorn -w 4 -b 0.0.0.0:5000 flask_app:app
```

---

## API Documentation

### Authentication Endpoints

#### Login
```http
POST /login
Content-Type: application/x-www-form-urlencoded

gmail=user@example.com&password=yourpassword
```

**Response:**
- Success: Redirect to main page
- Failure: Login page with error message

#### Signup
```http
POST /signup
Content-Type: application/x-www-form-urlencoded

gmail=user@example.com&password=yourpassword
```

**Response:**
- Success: Redirect to main page
- Failure: Signup page with error message

#### Logout
```http
GET /logout
```

**Response:** Redirect to login page

---

### Chat Endpoints

#### Send Message
```http
POST /chat
Content-Type: application/json

{
  "message": "Hello, how are you?",
  "stream": false  // Optional: enable streaming
}
```

**Response (non-streaming):**
```json
{
  "response": "I'm doing well, thank you for asking! How can I help you today?"
}
```

**Response (streaming):**
```
data: {"chunk": "I'm", "done": false}

data: {"chunk": " doing", "done": false}

data: {"chunk": " well", "done": false}

data: {"chunk": "", "done": true, "full_response": "I'm doing well"}
```

#### Initialize Application
```http
GET /api/init
```

**Response:**
```json
{
  "user": {
    "email": "user@example.com",
    "tier": "free",
    "theme": "dark",
    "personality": "default"
  },
  "active_session_id": "uuid-here",
  "sessions": {
    "uuid-here": {
      "name": "Chat 1",
      "history": [],
      "created": "2025-01-01 12:00:00"
    }
  },
  "history": [],
  "limits": {
    "allowed": true,
    "remaining": 2,
    "tier": "free"
  }
}
```

---

### Session Endpoints

#### Create Session
```http
POST /sessions/create
Content-Type: application/json

{
  "name": "New Chat"  // Optional
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "new-uuid",
  "sessions": { /* all sessions */ }
}
```

#### Switch Session
```http
POST /sessions/switch
Content-Type: application/json

{
  "session_id": "uuid-here"
}
```

**Response:**
```json
{
  "success": true,
  "history": [],
  "sessions": { /* all sessions */ }
}
```

#### Delete Session
```http
POST /sessions/delete
Content-Type: application/json

{
  "session_id": "uuid-here"
}
```

**Response:**
```json
{
  "success": true,
  "history": [],
  "sessions": { /* updated sessions */ },
  "active_session": "new-active-uuid"
}
```

#### Rename Session
```http
POST /sessions/rename
Content-Type: application/json

{
  "session_id": "uuid-here",
  "name": "New Name"
}
```

**Response:**
```json
{
  "success": true,
  "sessions": { /* updated sessions */ }
}
```

---

### Image Generation Endpoints

#### Generate Image
```http
POST /image
Content-Type: application/json

{
  "prompt": "A beautiful sunset over the ocean"
}
```

**Response:**
```json
{
  "success": true,
  "url": "/images/uuid-here.png",
  "id": "uuid-here",
  "dimensions": "1024x1024",
  "size_kb": 512.34,
  "thumbnail": "base64-encoded-thumbnail",
  "limits": {
    "remaining": 1,
    "next_reset": "2025-01-01T20:00:00",
    "tier": "free"
  }
}
```

#### Check Image Limit
```http
GET /image/check-limit
```

**Response:**
```json
{
  "allowed": true,
  "remaining": 2,
  "next_reset": "2025-01-01T20:00:00",
  "reset_seconds": 28800,
  "tier": "free"
}
```

---

### User Management Endpoints

#### Update Theme
```http
POST /theme
Content-Type: application/json

{
  "theme": "dark"
}
```

#### Update Personality
```http
POST /personality
Content-Type: application/json

{
  "personality": "funny"
}
```

#### Get User Profile
```http
GET /user/profile
```

**Response:**
```json
{
  "email": "user@example.com",
  "tier": "free",
  "tier_name": "Free",
  "images_used": 1,
  "images_limit": 2,
  "images_remaining": 1,
  "next_reset": "2025-01-01T20:00:00",
  "upgrade_history": []
}
```

#### Process Upgrade
```http
POST /upgrade/process
Content-Type: application/json

{
  "tier": "premium"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Upgraded to Premium tier successfully!",
  "new_tier": "premium",
  "tier_info": {
    "name": "Premium",
    "price": "$9.99/month"
  }
}
```

---

## Architecture

### Application Flow

```
                    ┌─────────────────┐
                    │   User Browser  │
                    └────────┬────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flask Application                        |
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Templates   │  │   REST API   │  │  Static Files    │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────┘   │
│         │                 │                                 │
│         ▼                 ▼                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                  Session Management                   │  │
│  │             (users.json / credentials.txt)            │  │
│  └──────────────────────────┬────────────────────────────┘  │
│                             │                               │
│                             ▼                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   OpenRouter API                    │    │
│  │       (Chat Completions / Image Generation)         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Data Models

#### User Data Structure
```json
{
  "email@example.com": {
    "sessions": {
      "uuid-1": {
        "name": "Chat 1",
        "history": [
          {
            "content": "Hello!",
            "sender": "user",
            "time": "2025-01-01 12:00:00"
          },
          {
            "content": "Hi there!",
            "sender": "bot",
            "time": "2025-01-01 12:00:01"
          }
        ],
        "created": "2025-01-01 12:00:00"
      }
    },
    "active_session": "uuid-1",
    "theme": "dark",
    "personality": "default",
    "tier": "free",
    "image_usage": {
      "last_reset": "2025-01-01T12:00:00",
      "count": 1
    },
    "upgrade_history": [
      {
        "from_tier": "free",
        "to_tier": "premium",
        "timestamp": "2025-01-01T12:00:00",
        "price": "$9.99/month"
      }
    ]
  }
}
```

#### Image Entry
```json
{
  "sender": "bot",
  "type": "image",
  "content": "[IMAGE:uuid]",
  "image_id": "uuid",
  "filename": "uuid.png",
  "prompt": "A beautiful sunset",
  "time": "2025-01-01 12:00:00",
  "image_info": {
    "width": 1024,
    "height": 1024,
    "size_kb": 512.34,
    "thumbnail": "base64..."
  }
}
```

### Middleware

- **Session Management**: Flask session with secret key encryption
- **Authentication Check**: Routes verify 'gmail' in session
- **Mobile Detection**: User-Agent based mobile detection
- **Rate Limiting**: Configurable request limits (via flask_limiter)

---

## User Tier System

| Tier      | Images/8hrs |   Price   |        Features        |
|-----------|-------------|-----------|------------------------|
|   Free    |      2      |    $0     | Basic image generation |
|  Premium  |     10      |  $9.99/mo |     Enhanced limits    |
| Unlimited |     100     | $19.99/mo |     Maximum access     |

### Reset Schedule
Image generation limits reset every 8 hours from the first usage.

---

## Security

### Implemented Security Measures
- ✅ Password hashing (in production, use bcrypt)
- ✅ Session-based authentication
- ✅ Input validation on all endpoints
- ✅ Secure HTTP headers
- ✅ CORS configuration (if needed)
- ✅ Rate limiting to prevent abuse

### Recommendations for Production
- Use HTTPS only
- Implement proper password hashing (bcrypt/argon2)
- Add CSRF protection
- Use environment variables for secrets
- Implement proper session timeout
- Add request logging and monitoring
- Use a proper database (PostgreSQL/MySQL)
- Implement backup strategies

---

## Deployment

### Docker Deployment (Recommended)

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["python", "flask_app.py"]
```

Build and run:
```bash
docker build -t hurairahgpt .
docker run -p 5000:5000 --env-file .env hurairahgpt
```

### Traditional Server Deployment

1. Set up server (Ubuntu recommended)
2. Install Python 3.11+
3. Clone repository
4. Install dependencies
5. Configure environment variables
6. Set up reverse proxy (nginx)
7. Configure SSL certificate
8. Use process manager (systemd/gunicorn)

---

## Troubleshooting

### Common Issues

#### 1. "API key not valid"
- Check `OPENROUTER_API_KEY` in `.env`
- Verify API key has proper permissions

#### 2. "Image generation failed"
- Check rate limits
- Verify tier has remaining quota
- Check network connectivity to OpenRouter

#### 3. "Session not found"
- User may have been logged out
- Session ID may be invalid
- Try refreshing the page

#### 4. "Rate limit exceeded"
- Wait for limit reset
- Upgrade to higher tier
- Check `rate_limits.json` configuration

### Logs
Check console output for detailed error messages and stack traces.

---

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

1. Fork the repository
2. Create feature branch
3. Make changes
4. Submit pull request

---

## License

Proprietary software. All rights reserved.

Copyright (c) 2025 Hurairah
All Rights Reserved.

---

## Support

- **Email**: hurairahgpt.devteam@gmail.com
- **Website**: https://talktohurairah.com
- **Issues**: [GitHub Issues](https://github.com/yourusername/hurairahgpt/issues)

---

## Technology Stack

| Technology | Purpose |
|------------|---------|
| Python | Backend language |
| Flask | Web framework |
| OpenAI SDK | AI API client |
| PIL | Image processing |
| Requests | HTTP client |
| Flask-Limiter | Rate limiting |

---

<div align="center">
  Made with ❤️ by Hurairah
</div>
