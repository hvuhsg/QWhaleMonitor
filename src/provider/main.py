from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from starlette.config import Config
from starlette.requests import Request
from authlib.integrations.starlette_client import OAuth

from db import DB

provider_login_app = APIRouter()

config = Config(env_file=".env")
oauth = OAuth(config)

oauth.register(
    name='provider',
    api_base_url='https://auth.qwhale.ml/',
    access_token_url='https://auth.qwhale.ml/token',
    authorize_url='https://auth.qwhale.ml/login',
    # api_base_url='http://127.0.0.1:8000/',
    # access_token_url='http://127.0.0.1:8000/token',
    # authorize_url='http://127.0.0.1:8000/login',
    access_token_params={
        "client_id": config.get("PROVIDER_CLIENT_ID"),
        "client_secret": config.get("PROVIDER_CLIENT_SECRET")
    }
)


@provider_login_app.get('/login')
async def login(request: Request):
    redirect_uri = request.url_for('auth')
    return await oauth.provider.authorize_redirect(request, redirect_uri)


@provider_login_app.get('/auth')
async def auth(request: Request):
    db = DB.get_instance()

    token = await oauth.provider.authorize_access_token(request)
    user = await oauth.provider.get(url="/me", token=token)
    user = user.json()

    token = user["identity_id"]
    first_login = False
    if not db.user_exist(token):
        db.add_user(token, user)
        first_login = True
    session_data = {"token": token, "first_time": first_login}

    request.session["user"] = session_data
    return RedirectResponse(url='/')


@provider_login_app.route("logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")
