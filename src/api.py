from fastapi import APIRouter, Depends, HTTPException, status, Request

from db import DB


api_app = APIRouter(tags=["api"])


def verify_token(request: Request, token: str = None) -> str:
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


@api_app.put("/site")
def add_site(
        site_name: str,
        site_url: str,
        timeout: float = None,
        scan_interval: float = None,
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
    site_id = db.add_site(
        site_name,
        site_url,
        timeout=timeout,
        filters=None,
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
