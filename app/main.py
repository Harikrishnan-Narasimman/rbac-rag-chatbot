from typing import Dict

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext


app = FastAPI()
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
@app.post("/chat")
def query(user=Depends(authenticate), message: str = "Hello"):
    return "Implement this endpoint."