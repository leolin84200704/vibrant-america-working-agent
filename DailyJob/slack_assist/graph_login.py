#!/usr/bin/env python3
"""One-time interactive Microsoft Graph login (device code) for the assistant.

Writes an MSAL token cache that assist_poll.py refreshes silently afterwards.
Uses the Microsoft Graph Command Line Tools public client; if the tenant blocks
user consent for it, IT has to register an app and you set ASSIST_GRAPH_CLIENT_ID.
"""
import os
import sys
from pathlib import Path

import msal

CLIENT_ID = os.environ.get("ASSIST_GRAPH_CLIENT_ID", "14d82eec-204b-4c2f-b7e8-296a70dab67e")
SCOPES = ["Mail.Read", "Mail.ReadWrite"]
CACHE = Path(os.environ.get("MS_GRAPH_TOKEN_CACHE", str(Path.home() / ".config/support-assist/msal_cache.json")))

cache = msal.SerializableTokenCache()
if CACHE.exists():
    cache.deserialize(CACHE.read_text())
app = msal.PublicClientApplication(CLIENT_ID, authority="https://login.microsoftonline.com/organizations", token_cache=cache)
flow = app.initiate_device_flow(scopes=SCOPES)
if "user_code" not in flow:
    print("device flow failed:", flow, file=sys.stderr)
    sys.exit(1)
print(flow["message"])
result = app.acquire_token_by_device_flow(flow)
if "access_token" not in result:
    print("login failed:", result.get("error"), result.get("error_description"), file=sys.stderr)
    sys.exit(1)
CACHE.parent.mkdir(parents=True, exist_ok=True)
CACHE.write_text(cache.serialize())
os.chmod(CACHE, 0o600)
print(f"token cache written to {CACHE}")
