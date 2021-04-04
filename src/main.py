import os
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from qwhale_logs_client import init

from provider.main import provider_login_app
from api import api_app

from db import DB
from config import DB_FILE_NAME
from monitor.main import Scanner

load_dotenv(".env")
session_secret = os.getenv("SESSION_SECRET")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=session_secret)
app.include_router(provider_login_app)
app.include_router(api_app)
scanner = None


@app.on_event("startup")
def startup():
    global scanner
    DB(DB_FILE_NAME)  # Create singleton instance
    scanner = Scanner(db=DB.get_instance())
    scanner.start()  # Start Scanning Thread
    init(token="VLUysQ9G7kVyaLj-fQWY7kYhZmA", project="monitor")


@app.on_event("shutdown")
def shutdown():
    global scanner
    scanner.stop()
    scanner.join()
