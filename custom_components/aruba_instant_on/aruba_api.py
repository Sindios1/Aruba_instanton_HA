import hashlib
import base64
import secrets
import json
import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, parse_qs

_LOGGER = logging.getLogger(__name__)

class ArubaInstantOnAPI:
    def __init__(self, username: str, password: str, session: aiohttp.ClientSession):
        self.username = username
        self.password = password
        self.session = session
        self.client_id = "987b543b-210d-9ed6-54a2-10a2c4567fa0"
        self.redirect_uri = "https://portal.arubainstanton.com"
        self.sso_url = "https://sso.arubainstanton.com"
        self.api_url = "https://nb.portal.arubainstanton.com/api"
        self.access_token = None

    def _generate_pkce(self):
        code_verifier = secrets.token_urlsafe(32)[:43]
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').replace('=', '').replace('+', '-').replace('/', '_')
        return code_verifier, code_challenge

    async def login(self) -> bool:
        try:
            # 1. Validate credentials and get session token
            login_data = {
                "username": self.username,
                "password": self.password
            }
            async with self.session.post(
                f"{self.sso_url}/aio/api/v1/mfa/validate/full",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            ) as resp:
                if resp.status != 200:
                    _LOGGER.error("Login failed with status %s", resp.status)
                    return False
                res_json = await resp.json()
                session_token = res_json.get("access_token")

            if not session_token:
                _LOGGER.error("Failed to get session token")
                return False

            # 2. Authorization request
            code_verifier, code_challenge = self._generate_pkce()
            state = secrets.token_urlsafe(32)[:43]
            
            auth_params = {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "scope": "profile openid",
                "state": state,
                "code_challenge_method": "S256",
                "code_challenge": code_challenge,
                "sessionToken": session_token
            }
            
            async with self.session.get(
                f"{self.sso_url}/as/authorization.oauth2",
                params=auth_params,
                allow_redirects=False
            ) as resp:
                location = resp.headers.get("Location")
                if not location:
                    _LOGGER.error("No redirect location found in auth response")
                    return False
                
                parsed_url = urlparse(location)
                auth_code = parse_qs(parsed_url.query).get("code", [None])[0]
            
            if not auth_code:
                _LOGGER.error("Failed to get authorization code")
                return False

            # 3. Exchange code for access token
            token_data = {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "code": auth_code,
                "code_verifier": code_verifier,
                "grant_type": "authorization_code"
            }
            
            async with self.session.post(
                f"{self.sso_url}/as/token.oauth2",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            ) as resp:
                if resp.status != 200:
                    _LOGGER.error("Token exchange failed with status %s", resp.status)
                    return False
                res_json = await resp.json()
                self.access_token = res_json.get("access_token")
            
            if self.access_token:
                # Store access token in session headers for subsequent requests
                self.session._default_headers.update({
                    "Authorization": f"Bearer {self.access_token}",
                    "x-ion-api-version": "7"
                })
                return True
            
            return False

        except Exception as e:
            _LOGGER.exception("Error during login")
            return False

    async def get_sites(self) -> List[Dict[str, Any]]:
        async with self.session.get(f"{self.api_url}/sites/") as resp:
            if resp.status == 401:
                if await self.login():
                    return await self.get_sites()
                return []
            res_json = await resp.json()
            return res_json.get("elements", [])

    async def get_inventory(self, site_id: str) -> List[Dict[str, Any]]:
        async with self.session.get(f"{self.api_url}/sites/{site_id}/inventory") as resp:
            res_json = await resp.json()
            return res_json.get("elements", [])

    async def get_clients(self, site_id: str) -> List[Dict[str, Any]]:
        async with self.session.get(f"{self.api_url}/sites/{site_id}/clientSummary") as resp:
            res_json = await resp.json()
            return res_json.get("elements", [])

    async def get_site_details(self, site_id: str) -> Dict[str, Any]:
        async with self.session.get(f"{self.api_url}/sites/{site_id}/landingPage") as resp:
            return await resp.json()
