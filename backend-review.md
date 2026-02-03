# HurairahGPT Backend Technical Review & Recommendations

## Executive Summary

The HurairahGPT backend demonstrates solid Flask architecture with clean API organization, but contains several **critical security vulnerabilities** and **scalability limitations** that must be addressed before production use. The file-based storage approach is suitable only for development/demo purposes.

---

## 1. Technical Review

### 1.1 Architecture Assessment

| Aspect | Current State | Grade | Notes |
|--------|--------------|-------|-------|
| Flask Structure | Modular routes | B | Clean separation of concerns |
| API Design | RESTful patterns | B | Good endpoint organization |
| State Management | Session-based | C | Works but limited |
| Error Handling | Basic try-catch | C | Missing standardized errors |
| Logging | Console output only | D | No structured logging |
| Testing | None mentioned | F | Critical gap |

### 1.2 Strengths

1. **Clean Endpoint Organization**
   - RESTful URL structure (`/sessions/create`, `/sessions/switch`)
   - Proper HTTP method usage
   - Good response format consistency

2. **Multi-Session Architecture**
   - Per-user session isolation
   - History persistence
   - Active session management

3. **AI Integration**
   - OpenRouter abstraction layer
   - Streaming support implemented
   - Model flexibility

### 1.3 Weaknesses (Demo-Level Choices)

1. **File-Based Storage**
   ```python
   # Current approach - NOT production-grade
   users = load_users_from_file()
   user_data = users.get(session["gmail"], {})
   ```
   - Race conditions on concurrent writes
   - No transaction support
   - Single point of failure
   - No backup mechanism

2. **Synchronous Processing**
   - All operations block
   - No async task queue for image generation
   - AI responses block the event loop

3. **In-Memory Rate Limiting**
   - Resets on server restart
   - Not distributed across instances
   - Memory leak potential

---

## 2. Security Audit

### 2.1 Critical Vulnerabilities

#### 🔴 CRITICAL: Password Storage
```python
# LIKELY CURRENT STATE (from documentation hints)
# Passwords stored in credentials.txt
# Documentation mentions bcrypt "in production" - implying plaintext now
```

**Risk Level:** CRITICAL
**Impact:** Complete account compromise
**Exploitability:** High

**Current State:**
- `credentials.txt` file contains email/password pairs
- Likely plaintext or weak hash
- No salt implementation
- No pepper (additional secret)

**Recommended Fix:**
```python
# Use argon2 for password hashing
import argon2
from secrets import token_bytes

class PasswordHasher:
    def __init__(self):
        self.ph = argon2.PasswordHasher(
            time_cost=3,           # Increase for production
            memory_cost=65536,     # 64MB
            parallelism=4,
            hash_len=32,
            salt_len=16
        )
    
    def hash(self, password: str) -> str:
        """Hash password with argon2"""
        return self.ph.hash(password)
    
    def verify(self, hashed: str, password: str) -> bool:
        """Verify password against hash"""
        try:
            return self.ph.verify(hashed, password)
        except argon2.exceptions.VerifyMismatchError:
            return False
    
    def needs_rehash(self, hashed: str) -> bool:
        """Check if hash needs upgrade"""
        return self.ph.check_needs_rehash(hashed)
```

**Migration Strategy:**
1. Add password hash column to users table
2. Create migration script for existing users
3. Force password reset on first login
4. Implement gradual migration

#### 🔴 CRITICAL: Session Security
```python
# Current Flask session configuration
# FLASK_SECRET_KEY=your-super-secret-key-change-in-production
```

**Issues:**
1. Secret key in environment variable (good) but may be leaked
2. No session expiration
3. No session rotation
4. No secure flag for cookies
5. No HttpOnly flag mentioned
6. No SameSite attribute

**Recommended Fix:**
```python
from datetime import timedelta

# Secure session configuration
app.config.update(
    SESSION_COOKIE_SECURE=True,        # HTTPS only
    SESSION_COOKIE_HTTPONLY=True,      # No JS access
    SESSION_COOKIE_SAMESITE='Lax',     # CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(hours=1),  # Session timeout
    SESSION_REFRESH_EACH_REQUEST=True,  # Refresh on activity
    SECRET_KEY=os.environ['FLASK_SECRET_KEY']
)
```

**Session Rotation Middleware:**
```python
@app.before_request
def session_management():
    """Rotate session ID periodically"""
    if 'gmail' not in session:
        return
    
    # Rotate session every 15 minutes
    last_rotation = session.get('last_rotation', 0)
    if time.time() - last_rotation > 900:  # 15 minutes
        session['last_rotation'] = time.time()
        # Flask handles session rotation via session.modified = True
        session.modified = True
```

#### 🟠 HIGH: File-Based Credentials Storage
```python
# Current approach
credentials.txt  # Contains user credentials
users.json       # Contains user data
rate_limits.json # Contains rate limit data
```

**Issues:**
1. No encryption at rest
2. World-readable files (likely)
3. No access control
4. Single file corruption = total data loss

**Recommended Fix:**
```python
# Move to database with encrypted fields
from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from cryptography.fernet import Fernet

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # argon2 hash
    # ... other fields
```

#### 🟠 HIGH: Missing CSRF Protection
```python
# Current: No CSRF tokens mentioned
@app.route("/login", methods=["POST"])
def login():
    # No CSRF validation
```

**Risk:** CSRF attacks on state-changing endpoints

**Recommended Fix:**
```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)
app.config['WTF_CSRF_CHECK_DEFAULT'] = False

# Enable CSRF for API endpoints
@app.after_request
def csrf_protection(response):
    # Add CSRF token to responses
    if 'csrf_token' not in response.headers.get('Set-Cookie', ''):
        token = generate_csrf()
        response.set_cookie('csrf_token', token, httponly=False, samesite='Lax')
    return response
```

#### 🟡 MEDIUM: Rate Limiting Bypass
```python
# Current: IP-based rate limiting in rate_limits.json
# Bypassable via:
# 1. Different IP addresses
# 2. Session cookie manipulation
# 3. VPN/proxy rotation
```

**Recommended Fix:**
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379",  # Redis for distributed limiting
    strategy="fixed-window"  # or "moving-window"
)

# Add user-based limiting for authenticated endpoints
@app.route("/chat", methods=["POST"])
@limiter.limit("10/minute", key_func=lambda: session.get('gmail'))
def chat():
    # ...
```

### 2.2 Security Checklist

| Security Measure | Status | Priority |
|-----------------|--------|----------|
| Password Hashing (bcrypt/argon2) | ❌ Missing | CRITICAL |
| Session Security (HttpOnly, Secure) | ❌ Missing | CRITICAL |
| CSRF Protection | ❌ Missing | HIGH |
| HTTPS Enforced | ❌ Not configured | HIGH |
| Rate Limiting (per-user) | ⚠️ Partial | HIGH |
| Input Sanitization | ⚠️ Basic | MEDIUM |
| SQL Injection Protection | ✅ Using parameterized queries | - |
| XSS Protection | ⚠️ Basic | MEDIUM |
| Audit Logging | ❌ Missing | MEDIUM |
| Account Lockout | ❌ Missing | MEDIUM |
| 2FA/MFA | ❌ Missing | LOW |

---

## 3. Scalability & Reliability Assessment

### 3.1 Current Storage Architecture

```
File-Based Storage (UNSUITABLE FOR PRODUCTION)
├── users.json         # User data (no transactions)
├── credentials.txt    # Credentials (no encryption)
├── rate_limits.json   # Rate limits (in-memory)
└── database.sqlite3   # (Exists but likely unused)
```

### 3.2 Scalability Issues

| Issue | Impact | Solution |
|-------|--------|----------|
| File I/O bottleneck | Single-threaded reads/writes | Database with connection pooling |
| No horizontal scaling | Can't add more servers | Stateless architecture + shared storage |
| No caching layer | Repeated DB/file reads | Redis cache |
| No async processing | Slow AI responses | Celery + Redis queue |
| No CDN integration | Static asset delivery | CloudFlare/R2 |

### 3.3 Migration Path: File → Database

#### Phase 1: SQLite (Quick Win)
```python
# database.py - SQLite implementation
import sqlite3
from contextlib import contextmanager
from flask import g

DATABASE = 'hurairahgpt.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database schema"""
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                theme TEXT DEFAULT 'dark',
                personality TEXT DEFAULT 'default',
                tier TEXT DEFAULT 'free',
                image_usage_count INTEGER DEFAULT 0,
                image_usage_last_reset TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT UNIQUE NOT NULL,
                name TEXT DEFAULT 'New Chat',
                history TEXT,  -- JSON stored as text
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        db.commit()
```

#### Phase 2: PostgreSQL (Production)
```python
# For production, upgrade to PostgreSQL
# Use SQLAlchemy for ORM
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    theme = db.Column(db.String(50), default='dark')
    personality = db.Column(db.String(50), default='default')
    tier = db.Column(db.String(50), default='free')
    image_usage_count = db.Column(db.Integer, default=0)
    image_usage_last_reset = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    sessions = db.relationship('Session', backref='user', lazy=True)

class Session(db.Model):
    __tablename__ = 'sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.String(36), unique=True, nullable=False)
    name = db.Column(db.String(255), default='New Chat')
    history = db.Column(db.JSON)  -- Native JSON support
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### 3.4 Reliability Improvements

#### Connection Management
```python
from contextlib import contextmanager
from sqlalchemy.pool import QueuePool

# Production database configuration
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'poolclass': QueuePool,
    'pool_size': 10,
    'max_overflow': 20,
    'pool_recycle': 3600,
    'pool_pre_ping': True,  # Verify connections
    'pool_timeout': 30,
}
```

#### Backup Strategy
```python
# Daily backup script
import shutil
from datetime import datetime
import subprocess

def backup_database():
    backup_dir = '/backups/hurairahgpt'
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'{backup_dir}/backup_{timestamp}.sql'
    
    # Create backup
    with open(backup_file, 'w') as f:
        subprocess.run(
            ['pg_dump', '-U', 'hurairahgpt', 'hurairahgpt'],
            stdout=f,
            check=True
        )
    
    # Upload to S3/cloud storage
    upload_to_cloud(backup_file)
    
    # Keep only last 7 days
    cleanup_old_backups(backup_dir, keep_days=7)
```

---

## 4. API & Streaming Improvements

### 4.1 Current Streaming Implementation

```python
# Current streaming (from documentation)
data: {"chunk": "I'm", "done": false}
data: {"chunk": " doing", "done": false}
```

**Issues:**
1. No reconnection handling
2. No heartbeat/keepalive
3. No sequence numbering
4. No error recovery

### 4.2 Improved Streaming Protocol

```python
import json
import uuid
from typing import Generator

def generate_streaming_response(user_message: str, session_id: str) -> Generator[str, None, None]:
    """Improved streaming with proper framing"""
    
    stream_id = str(uuid.uuid4())
    sequence = 0
    
    # Initial frame
    yield f"event: start\ndata: {json.dumps({'stream_id': stream_id})}\n\n"
    
    try:
        response = ""
        for chunk in openrouter.chat_completions_create(
            messages=[{"role": "user", "content": user_message}],
            stream=True
        ):
            content = chunk.choices[0].delta.content or ""
            if content:
                response += content
                sequence += 1
                yield f"event: chunk\ndata: {json.dumps({\n                    'stream_id': stream_id,\n                    'sequence': sequence,\n                    'chunk': content\n                })}\n\n"
        
        # Completion frame
        yield f"event: done\ndata: {json.dumps({\n            'stream_id': stream_id,\n            'sequence': sequence,\n            'full_response': response,\n            'usage': {'total_tokens': calculate_tokens(response)}\n        })}\n\n"
        
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({\n            'stream_id': stream_id,\n            'error': str(e)\n        })}\n\n"
```

### 4.3 Client-Side Reconnection Handler

```javascript
// Example reconnection logic for frontend
class StreamingClient {
    constructor(endpoint) {
        this.endpoint = endpoint;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
    }
    
    async connect(sessionId) {
        this.eventSource = new EventSource(`${this.endpoint}?session=${sessionId}`);
        
        this.eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.eventSource.onerror = () => {
            this.reconnect();
        };
    }
    
    reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            return;
        }
        
        setTimeout(() => {
            this.reconnectAttempts++;
            this.reconnectDelay *= 2;  // Exponential backoff
            this.connect();
        }, this.reconnectDelay);
    }
}
```

### 4.4 API Versioning Strategy

```python
# Versioned API endpoints
@app.route("/api/v1/chat", methods=["POST"])
def chat_v1():
    # Current implementation
    pass

@app.route("/api/v2/chat", methods=["POST"])
def chat_v2():  # Future improvements
    # With:
    # - Better error codes
    # - Response compression
    # - Rate limit headers
    pass
```

### 4.5 Standardized Error Responses

```python
class APIError(Exception):
    """Standardized API error"""
    
    def __init__(self, message: str, code: str, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

@app.errorhandler(APIError)
def handle_api_error(error):
    return jsonify({
        'error': {
            'code': error.code,
            'message': error.message,
            'timestamp': datetime.utcnow().isoformat(),
            'request_id': request.headers.get('X-Request-ID')
        }
    }), error.status_code

# Usage examples
raise APIError("Rate limit exceeded", "RATE_LIMIT_EXCEEDED", 429)
raise APIError("Invalid session", "INVALID_SESSION", 400)
raise APIError("Unauthorized", "UNAUTHORIZED", 401)
```

---

## 5. Architecture Evolution (100+ Concurrent Users)

### 5.1 Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer                             │
│                    (CloudFlare/HAProxy)                          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ Flask 1  │    │ Flask 2  │    │ Flask N  │
    │ (Gunicorn│    │ (Gunicorn│    │ (Gunicorn│
    │  Workers)│    │  Workers)│    │  Workers)│
    └────┬─────┘    └────┬─────┘    └────┬─────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
    ▼                    ▼                    ▼
┌─────────┐       ┌──────────┐        ┌──────────┐
│PostgreSQL│      │   Redis  │        │  S3/R2   │
│ (Primary)│      │  (Cache/ │        │ (Images) │
└─────────┘      │  Queue)   │        └──────────┘
                 └──────────┘
```

### 5.2 Component Specifications

| Component | Technology | Purpose | Cost Estimate |
|-----------|------------|---------|---------------|
| Load Balancer | CloudFlare/HAProxy | SSL termination, routing | $0-$50/month |
| API Servers | 2x 2GB VPS | Flask application | $20/month |
| Database | PostgreSQL (RDS/Supabase) | User/session data | $25/month |
| Cache/Queue | Redis (Upstash/RedisCloud) | Sessions, rate limits | $15/month |
| Storage | CloudFlare R2 | Image storage | $5/month |
| Monitoring | Prometheus + Grafana | Observability | $0 (self-hosted) |

**Total Monthly Cost: ~$70-100** (for 100-500 concurrent users)

### 5.3 AI Cost Control

```python
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta

@dataclass
class ModelConfig:
    name: str
    max_tokens: int
    cost_per_1k_tokens: float
    rpm_limit: int

# Model selection with cost awareness
MODEL_CONFIGS = {
    'cheap': ModelConfig(
        name='anthropic/claude-3-haiku',
        max_tokens=4000,
        cost_per_1k_tokens=0.001,
        rpm_limit=100
    ),
    'balanced': ModelConfig(
        name='anthropic/claude-3-sonnet',
        max_tokens=4000,
        cost_per_1k_tokens=0.003,
        rpm_limit=50
    ),
    'premium': ModelConfig(
        name='anthropic/claude-3-opus',
        max_tokens=4000,
        cost_per_1k_tokens=0.015,
        rpm_limit=20
    )
}

def select_model(tier: str, prompt_length: int) -> ModelConfig:
    """Select model based on user tier and prompt complexity"""
    if tier == 'free':
        return MODEL_CONFIGS['cheap']
    elif tier == 'premium':
        return MODEL_CONFIGS['balanced'] if prompt_length < 1000 else MODEL_CONFIGS['premium']
    else:  # unlimited
        return MODEL_CONFIGS['premium']
```

### 5.4 Task Queue for Image Generation

```python
# tasks.py - Celery tasks for async processing
from celery import Celery

celery_app = Celery(
    'tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1'
)

@celery_app.task(bind=True, max_retries=3)
def generate_image_task(self, prompt: str, user_email: str, session_id: str):
    """Generate image asynchronously"""
    try:
        # Check user limits before starting
        if not can_generate_image(user_email):
            raise Exception("Image generation limit reached")
        
        # Generate image
        result = openrouter.images.generate(
            model='bytedance-seed/seedream-4.5',
            prompt=prompt
        )
        
        # Save to storage
        image_url = save_image_to_s3(result.data[0].url, session_id)
        
        # Update user stats
        increment_image_usage(user_email)
        
        return {
            'success': True,
            'url': image_url,
            'id': result.id
        }
        
    except Exception as e:
        self.retry(exc=e, countdown=60)  # Retry in 60 seconds
```

---

## 6. Prioritized Action Items

### 🔴 Critical (Fix Before Production)

1. **Implement Password Hashing**
   - Add argon2 library
   - Create migration script
   - Force password reset for existing users
   - **Estimated Time:** 2-3 hours

2. **Configure Session Security**
   - Set Secure, HttpOnly, SameSite cookies
   - Add session timeout
   - Implement session rotation
   - **Estimated Time:** 1 hour

3. **Add CSRF Protection**
   - Install flask-wtf
   - Add CSRF tokens to forms
   - Protect API endpoints
   - **Estimated Time:** 2 hours

### 🟠 High (Fix Within 1 Month)

4. **Implement HTTPS**
   - Configure SSL certificate
   - Force HTTPS redirects
   - Update CORS settings
   - **Estimated Time:** 1 hour

5. **Add Rate Limiting (Redis)**
   - Install flask-limiter
   - Configure Redis storage
   - Implement per-user limits
   - **Estimated Time:** 2 hours

6. **Add Structured Logging**
   - Implement loguru
   - Add request IDs
   - Create log rotation
   - **Estimated Time:** 1-2 hours

### 🟡 Medium (Fix Within 3 Months)

7. **Migrate to SQLite**
   - Create database schema
   - Create data migration script
   - Update all data access functions
   - **Estimated Time:** 4-6 hours

8. **Add API Versioning**
   - Create /api/v1/ endpoints
   - Add error standardization
   - Implement request validation
   - **Estimated Time:** 4 hours

9. **Implement Proper Error Handling**
   - Create APIError class
   - Add error handlers
   - Create error response format
   - **Estimated Time:** 2 hours

### 🟢 Nice-to-Have (Future)

10. **Upgrade to PostgreSQL**
11. **Add Image Processing Queue (Celery)**
12. **Implement Monitoring (Prometheus)**
13. **Add CDN for Static Assets**
14. **Implement 2FA**
15. **Add Audit Logging**

---

## 7. Quick Wins (Under 1 Hour Each)

### 7.1 Environment Validation
```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

required_keys = ['FLASK_SECRET_KEY', 'OPENROUTER_API_KEY']
for key in required_keys:
    if not os.environ.get(key):
        raise EnvironmentError(f"Missing required environment variable: {key}")
```

### 7.2 Request ID Middleware
```python
import uuid

@app.before_request
def request_id():
    request.id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
    g.request_id = request.id

@app.after_request
def add_request_id(response):
    response.headers['X-Request-ID'] = request.id
    return response
```

### 7.3 Response Compression
```python
from flask_compress import Compress

compress = Compress(app)
app.config['COMPRESS_MIN_SIZE'] = 500
```

---

## 8. Testing Strategy

### 8.1 Required Tests

```python
# test_auth.py
import pytest
from flask import Flask

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            # Setup test database
            setup_test_db()
        yield client
        # Cleanup
        teardown_test_db()

def test_login_success(client):
    """Test successful login"""
    response = client.post('/login', data={
        'gmail': 'test@example.com',
        'password': 'correctpassword'
    }, follow_redirects=True)
    assert response.status_code == 200

def test_login_invalid_password(client):
    """Test login with invalid password"""
    response = client.post('/login', data={
        'gmail': 'test@example.com',
        'password': 'wrongpassword'
    })
    assert response.status_code == 401

def test_protected_route_requires_auth(client):
    """Test that protected routes require authentication"""
    response = client.get('/api/init')
    assert response.status_code == 401
```

### 8.2 Coverage Targets

| Component | Target Coverage |
|-----------|----------------|
| Authentication | 95% |
| Session Management | 90% |
| Chat API | 85% |
| Image Generation | 90% |
| Rate Limiting | 95% |
| **Overall Target** | **85%** |

---

## Summary

The HurairahGPT backend has a solid foundation but requires significant security hardening before production use. The immediate priorities are:

1. **Password Hashing** - Migrate from plaintext/weak hash to argon2
2. **Session Security** - Configure proper cookie attributes
3. **CSRF Protection** - Add token validation
4. **HTTPS** - Enforce SSL/TLS
5. **Rate Limiting** - Move to Redis-backed limiting

The file-based storage is acceptable for development but must be replaced with a proper database for any production deployment. A phased migration to SQLite (quick) → PostgreSQL (production) is recommended.

Total estimated effort for critical fixes: **8-10 hours**
Total estimated effort for high-priority fixes: **10-12 hours**
