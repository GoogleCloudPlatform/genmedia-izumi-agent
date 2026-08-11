# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Authentication utilities for Creative Studio integration."""

import logging
import urllib.parse
from google.auth.transport.requests import Request
from google.oauth2 import id_token

logger = logging.getLogger(__name__)


import google.auth


# JetSki generated I have my doubts about this one
def get_google_id_token(target_url: str) -> str | None:
    """Generates a Google OIDC ID token or OAuth2 access token for service-to-service authentication.

    If the target URL is local (localhost, 127.0.0.1) or not http/https,
    no token is needed and None is returned.
    """
    if not target_url:
        return None

    try:
        parsed = urllib.parse.urlparse(target_url)
        hostname = parsed.hostname or ""

        # Bypass for local endpoints
        if (
            hostname in ("localhost", "127.0.0.1")
            or hostname.startswith("10.")
            or hostname.startswith("192.168.")
        ):
            logger.debug(
                f"[AUTH] Target host '{hostname}' is local. Skipping token generation."
            )
            return None

        # 1. Try OIDC ID token (for Cloud Run service-to-service)
        audience = f"{parsed.scheme}://{parsed.netloc}"
        auth_req = Request()
        try:
            token = id_token.fetch_id_token(auth_req, audience)
            if token:
                return token
        except Exception:
            pass

        # 2. Try gcloud CLI identity token for local dev
        import subprocess

        try:
            token = subprocess.check_output(
                ["gcloud", "auth", "print-identity-token"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            if token:
                return token
        except Exception:
            pass

        # 3. Fallback to ADC OAuth2 access token
        creds, _ = google.auth.default()
        creds.refresh(auth_req)
        return creds.token
    except Exception as e:
        logger.warning(f"[AUTH] Failed to fetch Google authentication token: {e}")
        return None
