from pydantic import AnyHttpUrl
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from enum import Enum

from db import DB


api_app = APIRouter(tags=["api"])


def verify_token(request: Request, token: str = Query(default=None, description="Api token", title="API TOKEN")) -> str:
    db = DB.get_instance()
    if token is None and request.session.get("user", None) is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You must specify token or valid session")
    if token is None:
        token = request.session.get("user")["token"]
    if not db.user_exist(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Token!")
    return token


def verify_site_id(site_id: str, token=Depends(verify_token)) -> int:
    connected_token = DB.get_instance().connected_token(site_id)
    if connected_token is None or connected_token != token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The site is not your's!")
    return site_id


class Filter(str, Enum):
    """
    Filed to filter (notify on change)
    """
    status_code = "status_code"
    connection_error_to_connected = "connection_error_to_connected"
    connection_error_to_connection_error = "connection_error_to_connection_error"
    content_hash = "content_hash"
    url = "url"
    headers = "headers"
    links = "links"
    is_redirect = "is_redirect"
    is_permanent_redirect = "is_permanent_redirect"
    reason = "reason"
    history = "history"
    elapsed = "elapsed"


@api_app.api_route("/site", methods=["PUT", "POST"])
def add_site(
        site_name: str,
        site_url: AnyHttpUrl,
        filter1: Filter,
        filter2: Filter = None,
        filter3: Filter = None,
        timeout: float = None,
        scan_interval: float = Query(None, description="Scan site every X minutes"),
        token: str = Depends(verify_token),
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
    db = DB.get_instance()
    filters = list(filter(lambda x: x is not None, [filter1, filter2, filter3]))
    site_id = db.add_site(
        site_name,
        site_url,
        timeout=timeout,
        filters=filters,
        scan_interval=scan_interval
    )
    connected = db.connect_site_to_token(site_id, token)
    return {"site_id": site_id}


@api_app.delete("/site/{site_id}")
def delete_site(token=Depends(verify_token), site_id=Depends(verify_site_id)):
    return {"deleted": DB.get_instance().disable_site(site_id)}


@api_app.get("/sites")
def get_sites(token: str = Depends(verify_token)):
    db = DB.get_instance()
    sites = db.get_sites_by_token(token)
    return sites
