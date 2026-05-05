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
        self.redirect_uri = "https://portal.instant-on.hpe.com"
        self.sso_url = "https://sso.arubainstanton.com"
        self.api_url = "https://portal.instant-on.hpe.com/api"
        self.access_token = None
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def _aruba_base64_encode(self, data: bytes) -> str:
        """Specific Base64 encoding used by Aruba Instant On."""
        encoded = base64.b64encode(data).decode('utf-8')
        stripped = encoded.rstrip('=')
        padding_count = len(encoded) - len(stripped)
        # Aruba's custom encoding appends the number of padding characters
        custom_encoded = f"{stripped}{padding_count}"
        return custom_encoded.replace('+', '-').replace('/', '_')

    def _generate_pkce(self):
        # The PS script generates 32 bytes for the verifier
        verifier_bytes = secrets.token_bytes(32)
        code_verifier = self._aruba_base64_encode(verifier_bytes)[:43]
        
        sha256_hash = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = self._aruba_base64_encode(sha256_hash)[:43]
        
        _LOGGER.debug("Generated PKCE - Verifier: %s, Challenge: %s", code_verifier, code_challenge)
        return code_verifier, code_challenge

    async def login(self) -> bool:
        try:
            # 0. Fetch dynamic settings to get Client ID
            async with self.session.get("https://portal.instant-on.hpe.com/settings.json") as resp:
                settings = await resp.json()
                self.client_id = settings.get("ssoClientIdAuthZ", self.client_id)
                _LOGGER.debug("Using Client ID: %s", self.client_id)

            # 1. Validate credentials and get session token
            login_data = {
                "username": self.username,
                "password": self.password,
                "client_id": self.client_id
            }
            _LOGGER.debug("Attempting initial validation for user: %s", self.username)
            async with self.session.post(
                f"{self.sso_url}/aio/api/v1/mfa/validate/full",
                data=login_data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "Origin": "https://portal.instant-on.hpe.com",
                    "Referer": "https://portal.instant-on.hpe.com/"
                }
            ) as resp:
                if resp.status != 200:
                    resp_text = await resp.text()
                    _LOGGER.error("Initial validation failed with status %s: %s", resp.status, resp_text)
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
                _LOGGER.debug("Authorization response status: %s", resp.status)
                location = resp.headers.get("Location")
                if not location:
                    _LOGGER.error("No redirect location found in auth response. Status: %s, Body: %s", resp.status, await resp.text())
                    return False
                
                _LOGGER.debug("Redirect location: %s", location)
                parsed_url = urlparse(location)
                auth_code = parse_qs(parsed_url.query).get("code", [None])[0]
            
            if not auth_code:
                _LOGGER.error("Failed to get authorization code from location: %s", location)
                return False

            # 3. Exchange code for access token
            token_data = {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "code": auth_code,
                "code_verifier": code_verifier,
                "grant_type": "authorization_code"
            }
            
            _LOGGER.debug("Exchanging code for token")
            async with self.session.post(
                f"{self.sso_url}/as/token.oauth2",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            ) as resp:
                if resp.status != 200:
                    _LOGGER.error("Token exchange failed with status %s: %s", resp.status, await resp.text())
                    return False
                res_json = await resp.json()
                self.access_token = res_json.get("access_token")
                _LOGGER.debug("Successfully obtained access token")
            
            if self.access_token:
                self._headers.update({
                    "Authorization": f"Bearer {self.access_token}",
                    "x-ion-api-version": "7",
                    "Content-Type": "application/json"
                })
                return True
            
            return False

        except Exception as e:
            _LOGGER.exception("Error during login")
            return False

    async def get_sites(self) -> List[Dict[str, Any]]:
        try:
            async with self.session.get(f"{self.api_url}/sites/", headers=self._headers) as resp:
                if resp.status == 401:
                    _LOGGER.debug("Access token expired, re-logging")
                    if await self.login():
                        return await self.get_sites()
                    return []
                resp.raise_for_status()
                res_json = await resp.json()
                return res_json.get("elements", [])
        except Exception as e:
            _LOGGER.error("Failed to get sites: %s", e)
            return []

    async def get_inventory(self, site_id: str) -> List[Dict[str, Any]]:
        async with self.session.get(f"{self.api_url}/sites/{site_id}/inventory", headers=self._headers) as resp:
            resp.raise_for_status()
            res_json = await resp.json()
            return res_json.get("elements", [])

    async def get_clients(self, site_id: str) -> List[Dict[str, Any]]:
        async with self.session.get(f"{self.api_url}/sites/{site_id}/clientSummary", headers=self._headers) as resp:
            resp.raise_for_status()
            res_json = await resp.json()
            return res_json.get("elements", [])

    async def get_site_details(self, site_id: str) -> Dict[str, Any]:
        async with self.session.get(f"{self.api_url}/sites/{site_id}/landingPage", headers=self._headers) as resp:
            resp.raise_for_status()
            return await resp.json()
