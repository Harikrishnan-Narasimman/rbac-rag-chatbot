from typing import Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext
from groq import APIError, RateLimitError 

from app.schemas.chat import ChatRequest, ChatResponse
from app.services import rag
from app.services.vectorstore import get_vectorstore

@asynccontextmanager
async def lifespan(app: FastAPI):
    get_vectorstore()
    yield


app = FastAPI(lifespan=lifespan)
security = HTTPBasic()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Dummy user database
users_db: Dict[str, Dict[str, str]] = {
    "Tony": {"password": pwd_context.hash("password123"), "role": "engineering"},
    "Bruce": {"password": pwd_context.hash("securepass"), "role": "marketing"},
    "Sam": {"password": pwd_context.hash("financepass"), "role": "finance"},
    "Peter": {"password": pwd_context.hash("pete123"), "role": "engineering"},
    "Sid": {"password": pwd_context.hash("sidpass123"), "role": "marketing"},
    "Natasha": {"password": pwd_context.hash("hrpass123"), "role": "hr"},
    "Hari": {"password": pwd_context.hash("haripass123"), "role": "general"},
    "Nick": {"password": pwd_context.hash("ceopass123"), "role": "c-level"},
}


# Authentication dependency
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    username = credentials.username
    password = credentials.password
    user = users_db.get(username)
    if not user or not pwd_context.verify(password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"username": username, "role": user["role"]}


# Login endpoint
@app.get("/login")
def login(user=Depends(authenticate)):
    return {"message": f"Welcome {user['username']}!", "role": user["role"]}


# Protected test endpoint
@app.get("/test")
def test(user=Depends(authenticate)):
    return {"message": f"Hello {user['username']}! You can now chat.", "role": user["role"]}


# Protected chat endpoint
@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, user=Depends(authenticate)):
    try:
        return rag.answer(request.message, user["role"])
    except RateLimitError:
        raise HTTPException(status_code=429, detail="LLM rate limit reached, try again shortly.")
    except APIError:
        raise HTTPException(status_code=502, detail="The language model service is unavailable.")