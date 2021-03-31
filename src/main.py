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


def verify_site_id(site_id: str, token=Depends(verify_token)) -> int:
    connected_token = DB.get_instance().connected_token(site_id)
    if connected_token is None or connected_token != token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The site is not your's!")
    return site_id


@app.put("/site")
def add_site(
        site_name: str,
        site_url: str,
        timeout: float = None,
        scan_interval: float = None,
        token=Depends(verify_token),
) -> int:
    """
    Register new website to the system\n

    :param site_name: The web site name\n
    :param site_url: The website url including http / https\n
    :param timeout: request timeout\n
    :param filters: list of fields to notify if changing\n
    :param scan_interval: website scanning interval\n
    :param token: your system token\n
    :return: {'site_id': <id>}\n
    """
    site_id = DB.get_instance().add_site(
        site_name,
        site_url,
        timeout=timeout,
        filters=None,
        scan_interval=scan_interval
    )
    return {"site_id": site_id}


@app.delete("/site/{site_id}")
def delete_site(token=Depends(verify_token), site_id=Depends(verify_site_id)):
    return {"deleted": DB.get_instance().disable_site(site_id)}


@app.get("/sites")
def get_sites(token: str = Depends(verify_token)):
    db = DB.get_instance()
    sites = db.get_sites_by_token(token)
    return sites
