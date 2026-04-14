"""
Enhanced Backend Server with Authentication
=========================================
Includes authentication endpoints and basic functionality for login testing.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import hashlib
import secrets
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup (using SQLite for simplicity)
DB_PATH = "news_platform.db"

def init_db():
    """Initialize SQLite database with admin user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create admin_users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'admin',
            is_active BOOLEAN DEFAULT 1,
            last_login_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create default admin user if not exists
    cursor.execute("SELECT * FROM admin_users WHERE username = 'admin'")
    if not cursor.fetchone():
        password_hash = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute("""
            INSERT INTO admin_users (username, password_hash, email, role, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, ("admin", password_hash, "admin@newsplatform.local", "admin", 1))
        logger.info("Created default admin user: admin/admin123")
    
    conn.commit()
    conn.close()

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    username: str
    role: str

class UserInfo(BaseModel):
    id: int
    username: str
    email: str
    role: str

# Simple JWT-like token handling
SECRET_KEY = "your-secret-key-change-in-production"
security = HTTPBearer()

def create_token(username: str, role: str) -> str:
    """Create a simple token (in production, use proper JWT)."""
    payload = f"{username}:{role}:{secrets.token_hex(16)}"
    return secrets.token_urlsafe(32)

def verify_token(token: str) -> Optional[dict]:
    """Verify token and return payload (simplified)."""
    # In production, use proper JWT verification
    # For now, we'll create a simple token store
    if not hasattr(verify_token, 'token_store'):
        verify_token.token_store = {}
    
    if token in verify_token.token_store:
        return verify_token.token_store[token]
    return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current user from token."""
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting News Platform Backend...")
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down...")

# Create FastAPI app
app = FastAPI(
    title="News Platform Backend",
    description="AI-powered news aggregation platform backend",
    version="2.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000", 
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Authentication endpoints
@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return token."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, username, password_hash, email, role, is_active FROM admin_users WHERE username = ? AND is_active = 1",
        (request.username,)
    )
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    user_id, username, password_hash, email, role, is_active = user
    # Verify password
    input_hash = hashlib.sha256(request.password.encode()).hexdigest()
    if input_hash != password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Create token
    token = create_token(username, role)
    
    # Store token (in production, use proper JWT with expiration)
    if not hasattr(verify_token, 'token_store'):
        verify_token.token_store = {}
    verify_token.token_store[token] = {
        "id": user_id,
        "username": username,
        "email": email,
        "role": role
    }
    
    # Update last login
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE admin_users SET last_login_at = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), user_id)
    )
    conn.commit()
    conn.close()
    
    logger.info(f"User {username} logged in successfully")
    return TokenResponse(
        access_token=token,
        username=username,
        role=role
    )

@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info."""
    return current_user

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "News Platform Backend",
        "version": "2.1.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.1.0"}

@app.get("/api/test")
async def test_endpoint():
    """Test endpoint for debugging."""
    return {"message": "Backend is working", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8005, reload=True)
