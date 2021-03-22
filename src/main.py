from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, status

from db import DB
from config import DB_FILE_NAME
from monitor.main import Scanner

app = FastAPI()
scanner = None


@app.on_event("startup")
def startup():
    global scanner
    DB(DB_FILE_NAME)  # Create singleton instance
    scanner = Scanner(db=DB.get_instance())
    scanner.start()  # Start Scanning Thread


@app.on_event("shutdown")
def shutdown():
    global scanner
    scanner.stop()
    scanner.join()


def verify_token(token: str) -> str:
    if token != "HardCodedToken!":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Token!")
    return token


def verify_site_id(site_id: int, token=Depends(verify_token)) -> int:
    connected_token = DB.get_instance().connected_token(site_id)
    if connected_token is None or connected_token != token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The site is not your's!")
    return site_id


@app.put("/site")
def add_site(
        site_name: str,
        site_url: str,
        timeout: float = None,
        filters: List[str] = None,
        token=Depends(verify_token),
) -> int:
    site_id = DB.get_instance().add_site(site_name, site_url, timeout=timeout, filters=filters)
    return {"site_id": site_id}


@app.delete("/site/{site_id}")
def delete_site(token=Depends(verify_token), site_id=Depends(verify_site_id)):
    return {"deleted": DB.get_instance().disable_site(site_id)}
