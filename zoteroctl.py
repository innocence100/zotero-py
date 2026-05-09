#!/usr/bin/env python3
"""Manage users for the Zotero sync server."""

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request


def _load_dotenv():
    """Load environment variables from ./.env if present."""
    env_path = pathlib.Path(__file__).with_name(".env")
    if not env_path.exists():
        return
    with env_path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                if key not in os.environ:
                    os.environ[key] = value.strip()


_load_dotenv()


def get_base_url():
    return os.environ.get("ZOTERO_URL", "http://localhost:8080")

def get_admin_token():
    return os.environ.get("ZOTERO_ADMIN_TOKEN", "admin-token")

def req(method, url, data=None, headers=None):
    headers = headers or {}
    if data is not None and isinstance(data, (dict, list)):
        data = json.dumps(data).encode()
        headers.setdefault("Content-Type", "application/json")
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        resp = urllib.request.urlopen(r)
        body = resp.read().decode()
        return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            j = json.loads(body)
        except:
            j = {"detail": body}
        return e.code, j

def create_user(username, password):
    base = get_base_url()
    s, d = req("POST", f"{base}/admin/users",
               {"username": username, "password": password},
               {"Authorization": f"Bearer {get_admin_token()}"})
    if s == 200:
        print(f"User created: {d['username']} (id={d['id']}, library_id={d['library_id']})")
        print(f"API key: {d['api_key']}")
    elif s == 400 or s == 409:
        print(f"Error: {d.get('detail', d)}")
    else:
        print(f"Error (status {s}): {d}")

def list_users():
    base = get_base_url()
    s, d = req("GET", f"{base}/admin/users",
               headers={"Authorization": f"Bearer {get_admin_token()}"})
    if s != 200:
        print(f"Error (status {s}): {d}")
        return
    if not d:
        print("No users.")
        return
    for u in d:
        keys = ", ".join(k["key"] for k in u.get("api_keys", []))
        print(f"  id={u['id']}  username={u['username']}  library={u['library_id']}  key={keys}")

def delete_user(user_id):
    base = get_base_url()
    s, d = req("DELETE", f"{base}/admin/users/{user_id}",
               headers={"Authorization": f"Bearer {get_admin_token()}"})
    if s == 200:
        print(f"User {user_id} deleted.")
    else:
        print(f"Error (status {s}): {d}")

def usage():
    print("Usage:")
    print(f"  {sys.argv[0]} create <username> <password>   Create a user")
    print(f"  {sys.argv[0]} list                          List all users")
    print(f"  {sys.argv[0]} delete <user_id>               Delete a user")
    print()
    print("Environment variables:")
    print("  ZOTERO_URL         Server URL (default: http://localhost:8080)")
    print("  ZOTERO_ADMIN_TOKEN Admin token (default: admin-token)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "create":
        if len(sys.argv) < 4:
            print("Usage: {sys.argv[0]} create <username> <password>")
            sys.exit(1)
        create_user(sys.argv[2], sys.argv[3])
    elif cmd == "list":
        list_users()
    elif cmd == "delete":
        if len(sys.argv) < 3:
            print(f"Usage: {sys.argv[0]} delete <user_id>")
            sys.exit(1)
        delete_user(sys.argv[2])
    else:
        usage()
        sys.exit(1)
