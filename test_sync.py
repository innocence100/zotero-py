#!/usr/bin/env python3
"""Protocol-aware test for Zotero sync server."""

import json
import os
import sys
import urllib.request
import urllib.error

BASE = os.environ.get("ZOTERO_TEST_URL", "http://localhost:8080")
ADMIN_TOKEN = os.environ.get("ZOTERO_ADMIN_TOKEN", "test-admin-token")
USERNAME = "testuser"
PASSWORD = "testpass"
BOOK_KEY = "BKAAAAAA"
ARTICLE_KEY = "JAAAAAAA"
NOTE_KEY = "NTAAAAAA"
COLL_KEY = "CLAAAAAA"
CHILD_COLL_KEY = "CLAAAAAB"
SEARCH_KEY = "SRAAAAAA"


def req(method, url, data=None, headers=None):
    headers = headers or {}
    if data is not None:
        if isinstance(data, (dict, list)):
            data = json.dumps(data).encode()
            headers.setdefault("Content-Type", "application/json")
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        resp = urllib.request.urlopen(r)
        body = resp.read().decode()
        hdrs = {k.lower(): v for k, v in resp.headers.items()}
        try:
            j = json.loads(body) if body else None
        except json.JSONDecodeError:
            j = body
        return resp.status, j, hdrs
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            j = json.loads(body)
        except Exception:
            j = body
        return e.code, j, dict(e.headers)


def test(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    msg = f"[{status}] {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    if not condition:
        global failures
        failures += 1


failures = 0

print("=" * 60)
print("Step 0: Create user via admin API")
print("=" * 60)
s, d, h = req("POST", f"{BASE}/admin/users",
              {"username": USERNAME, "password": PASSWORD},
              {"Authorization": f"Bearer {ADMIN_TOKEN}"})
test("Create user", s == 200, f"status={s}")
if s != 200:
    print("FATAL: cannot create user")
    sys.exit(1)
LIB_ID = d["id"]
KEY = d["api_key"]
H = {"Zotero-API-Key": KEY}

print("\n" + "=" * 60)
print("Step 1: Login via POST /keys")
print("=" * 60)
s, d, h = req("POST", f"{BASE}/keys", {
    "username": USERNAME,
    "password": PASSWORD,
    "name": "Automatic Zotero Client Key",
    "access": {
        "user": {"library": True, "notes": True, "write": True, "files": True},
        "groups": {"all": {"library": True, "write": True}}
    }
})
test("Login returns 201", s == 201, f"status={s}")
test("Response has key", d.get("key") is not None)

print("\n" + "=" * 60)
print("Step 2: Verify key — GET /keys/current")
print("=" * 60)
s, d, h = req("GET", f"{BASE}/keys/current", headers=H)
test("Key valid", s == 200)

print("\n" + "=" * 60)
print("Step 3: Full download sync (empty library)")
print("=" * 60)
s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/items?format=versions&since=0", headers=H)
test("Items empty", s == 200 and d == {})
test("Has Last-Modified-Version", "last-modified-version" in h)

s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/settings", headers=H)
test("Settings empty", s == 200 and d == {})

s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/deleted?since=0", headers=H)
test("Deleted empty", s == 200 and d.get("items") == [])

print("\n" + "=" * 60)
print("Step 4: Upload items")
print("=" * 60)
items = [
    {"itemType": "book", "key": BOOK_KEY, "title": "Book A",
     "creators": [{"creatorType": "author", "firstName": "A", "lastName": "B"}],
     "tags": [{"tag": "programming"}], "collections": [], "relations": {}},
    {"itemType": "journalArticle", "key": ARTICLE_KEY, "title": "Article A",
     "creators": [{"creatorType": "author", "firstName": "C", "lastName": "D"}],
     "tags": [{"tag": "deep-learning"}], "collections": [], "relations": {}},
    {"itemType": "note", "key": NOTE_KEY, "note": "<p>Note</p>",
     "parentItem": ARTICLE_KEY, "tags": [], "collections": [], "relations": {}},
]
s, d, h = req("POST", f"{BASE}/users/{LIB_ID}/items", items, H)
test("Create items 200", s == 200)
test("All succeeded", len(d.get("successful", {})) == 3,
     f"success={len(d.get('successful', {}))}, failed={d.get('failed', {})}")
upload_ver = int(h.get("last-modified-version", 0))

test("Write report has data.key", d["successful"]["0"]["data"]["key"] == BOOK_KEY)
test("Write report has data.version", isinstance(d["successful"]["0"]["data"]["version"], int))

print("\n" + "=" * 60)
print("Step 5: Upload collections")
print("=" * 60)
s, d, h = req("POST", f"{BASE}/users/{LIB_ID}/collections", [
    {"key": COLL_KEY, "name": "Books"},
    {"key": CHILD_COLL_KEY, "name": "Papers", "parentCollection": COLL_KEY},
], H)
test("Create collections", len(d.get("successful", {})) == 2)

print("\n" + "=" * 60)
print("Step 6: Upload settings")
print("=" * 60)
s, d, h = req("POST", f"{BASE}/users/{LIB_ID}/settings", {
    "tagColors": {"value": [{"name": "programming", "color": "#CC0000"}]}
}, H)
test("Settings saved 204", s == 204)
settings_ver = int(h.get("last-modified-version", 0))

print("\n" + "=" * 60)
print("Step 7: Verify settings format {value, version}")
print("=" * 60)
s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/settings", headers=H)
test("Settings has tagColors", "tagColors" in d)
test("tagColors has value key", isinstance(d.get("tagColors", {}).get("value"), list))
test("tagColors has version key", isinstance(d.get("tagColors", {}).get("version"), int))

tagcolors_ver = d["tagColors"]["version"]

print("\n" + "=" * 60)
print("Step 7b: PUT /settings/{name} version checks")
print("=" * 60)
# New setting without version → 428
s, d, h = req("PUT", f"{BASE}/users/{LIB_ID}/settings/newput",
              {"value": "test"}, H)
test("PUT new setting without version → 428", s == 428, f"status={s}")

# New setting with stale version → 412
s, d, h = req("PUT", f"{BASE}/users/{LIB_ID}/settings/newput",
              {"value": "test"},
              {**H, "If-Unmodified-Since-Version": "1"})
test("PUT new setting with version 1 → 412", s == 412, f"status={s}")

# New setting with version 0 → 204
s, d, h = req("PUT", f"{BASE}/users/{LIB_ID}/settings/newput",
              {"value": "test"},
              {**H, "If-Unmodified-Since-Version": "0"})
test("PUT new setting with version 0 → 204", s == 204, f"status={s}")
put_ver = int(h.get("last-modified-version", 0))

# Update setting with stale version → 412
s, d, h = req("PUT", f"{BASE}/users/{LIB_ID}/settings/newput",
              {"value": "updated"},
              {**H, "If-Unmodified-Since-Version": str(put_ver - 1)})
test("PUT existing setting with stale version → 412", s == 412, f"status={s}")

# Update setting with correct version → 204
s, d, h = req("PUT", f"{BASE}/users/{LIB_ID}/settings/newput",
              {"value": "updated"},
              {**H, "If-Unmodified-Since-Version": str(put_ver)})
test("PUT existing setting with correct version → 204", s == 204, f"status={s}")

# Update existing setting from JSON body version
s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/settings/tagColors", headers=H)
tc_ver = d["version"]
s, d, h = req("PUT", f"{BASE}/users/{LIB_ID}/settings/tagColors",
              {"value": [{"name": "_READ", "color": "#990000"}], "version": tc_ver},
              H)
test("PUT existing setting with JSON version → 204", s == 204, f"status={s}")

# Stale JSON version → 412
s, d, h = req("PUT", f"{BASE}/users/{LIB_ID}/settings/tagColors",
              {"value": [{"name": "_READ", "color": "#CC0000"}], "version": tc_ver - 1},
              H)
test("PUT existing setting with stale JSON version → 412", s == 412, f"status={s}")

print("\n" + "=" * 60)
print("Step 8: includeTrashed=1")
print("=" * 60)
s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/items?format=versions&since=0&includeTrashed=1", headers=H)
test("includeTrashed returns items", len(d) >= 3)

print("\n" + "=" * 60)
print("Step 9: format=keys")
print("=" * 60)
s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/collections?format=keys", headers=H)
test("keys returns 200", s == 200)
test("keys is text/plain", "text/plain" in h.get("content-type", ""))
test("keys has entries", len(d.strip().split("\n")) >= 2 if d.strip() else False)

print("\n" + "=" * 60)
print("Step 10: Single-object PUT returns 204")
print("=" * 60)
s_item, d_item, h_item = req("GET", f"{BASE}/users/{LIB_ID}/items/{BOOK_KEY}", headers=H)
item_ver = d_item["version"]
s, d, h = req("PUT", f"{BASE}/users/{LIB_ID}/items/{BOOK_KEY}",
              {"itemType": "book", "key": BOOK_KEY, "version": item_ver,
               "creators": [{"creatorType": "author", "firstName": "A", "lastName": "B"}],
               "title": "Book A Updated"},
              {**H, "If-Unmodified-Since-Version": str(item_ver)})
test("PUT returns 204", s == 204, f"status={s}")
test("PUT has Last-Modified-Version", "last-modified-version" in h)

print("\n" + "=" * 60)
print("Step 11: 428 — write without version")
print("=" * 60)
s, d, h = req("PUT", f"{BASE}/users/{LIB_ID}/items/{BOOK_KEY}",
              {"itemType": "book", "title": "No Version"}, H)
test("428 without version", s == 428, f"status={s}")

print("\n" + "=" * 60)
print("Step 12: 412 — stale version")
print("=" * 60)
s, d, h = req("PUT", f"{BASE}/users/{LIB_ID}/items/{BOOK_KEY}",
              {"itemType": "book", "title": "Stale"},
              {**H, "If-Unmodified-Since-Version": "1"})
test("412 on stale version", s == 412, f"status={s}")

print("\n" + "=" * 60)
print("Step 13: PATCH merge — does not delete missing fields")
print("=" * 60)
s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/items/{BOOK_KEY}", headers=H)
item_ver = d["version"]
s, d, h = req("PATCH", f"{BASE}/users/{LIB_ID}/items/{BOOK_KEY}",
              {"key": BOOK_KEY, "version": item_ver, "title": "Book A Patched"},
              {**H, "If-Unmodified-Since-Version": str(item_ver)})
test("PATCH returns 204", s == 204, f"status={s}")
s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/items/{BOOK_KEY}", headers=H)
test("PATCH preserved creators", len(d["data"].get("creators", [])) == 1,
     f"creators={d['data'].get('creators')}")

print("\n" + "=" * 60)
print("Step 14: Delete item (with version)")
print("=" * 60)
s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/items/{ARTICLE_KEY}", headers=H)
ja_ver = d["version"]
before_ver = int(h.get("last-modified-version", settings_ver))

s, d, h = req("DELETE", f"{BASE}/users/{LIB_ID}/items/{ARTICLE_KEY}", headers={
    **H, "If-Unmodified-Since-Version": str(ja_ver)
})
test("Delete item 204", s == 204, f"status={s}")

s, d, h = req("DELETE", f"{BASE}/users/{LIB_ID}/collections/{CHILD_COLL_KEY}", headers={
    **H, "If-Unmodified-Since-Version": str(before_ver)
})
test("Delete collection 204", s == 204, f"status={s}")

s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/deleted?since={before_ver}", headers=H)
test("Delete log has item", ARTICLE_KEY in d.get("items", []))
test("Delete log has collection", CHILD_COLL_KEY in d.get("collections", []))
current_ver = int(h.get("last-modified-version", before_ver))

print("\n" + "=" * 60)
print("Step 15: Delete item without version → 428")
print("=" * 60)
s, d, h = req("DELETE", f"{BASE}/users/{LIB_ID}/items/{BOOK_KEY}", headers=H)
test("428 on delete without version", s == 428, f"status={s}")

print("\n" + "=" * 60)
print("Step 16: Tag deletion")
print("=" * 60)
s, d, h = req("DELETE", f"{BASE}/users/{LIB_ID}/tags?tags=programming",
              headers={**H, "If-Unmodified-Since-Version": str(current_ver)})
test("Tag delete 204", s == 204, f"status={s}")

print("\n" + "=" * 60)
print("Step 17: Search single-object endpoints")
print("=" * 60)
s, d, h = req("POST", f"{BASE}/users/{LIB_ID}/searches", [
    {"key": SEARCH_KEY, "name": "My Search",
     "conditions": [{"condition": "title", "operator": "contains", "value": "test"}]}
], H)
test("Create search", len(d.get("successful", {})) == 1)
s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/searches/{SEARCH_KEY}", headers=H)
test("Get search 200", s == 200, f"status={s}")
sr_ver = d["version"]
s, d, h = req("PATCH", f"{BASE}/users/{LIB_ID}/searches/{SEARCH_KEY}",
              {"key": SEARCH_KEY, "version": sr_ver, "name": "Patched Search"},
              {**H, "If-Unmodified-Since-Version": str(sr_ver)})
test("PATCH search 204", s == 204, f"status={s}")

print("\n" + "=" * 60)
print("Step 18: Batch stale versions do not overwrite remote data")
print("=" * 60)
s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/items/{BOOK_KEY}", headers=H)
remote_item_ver = d["version"]
s, d, h = req("PATCH", f"{BASE}/users/{LIB_ID}/items/{BOOK_KEY}",
              {"key": BOOK_KEY, "version": remote_item_ver, "title": "Remote Item Wins"},
              {**H, "If-Unmodified-Since-Version": str(remote_item_ver)})
test("Remote item update 204", s == 204, f"status={s}")
s, d, h = req("POST", f"{BASE}/users/{LIB_ID}/items", [
    {"key": BOOK_KEY, "version": remote_item_ver, "itemType": "book", "title": "Stale Batch Item"}
], H)
test("Stale batch item failed 412", d.get("failed", {}).get("0", {}).get("code") == 412,
     f"failed={d.get('failed', {})}")
s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/items/{BOOK_KEY}", headers=H)
test("Stale batch item did not overwrite", d["data"].get("title") == "Remote Item Wins",
     f"title={d['data'].get('title')}")

s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/collections/{COLL_KEY}", headers=H)
remote_coll_ver = d["version"]
s, d, h = req("PATCH", f"{BASE}/users/{LIB_ID}/collections/{COLL_KEY}",
              {"key": COLL_KEY, "version": remote_coll_ver, "name": "Remote Collection Wins"},
              {**H, "If-Unmodified-Since-Version": str(remote_coll_ver)})
test("Remote collection update 204", s == 204, f"status={s}")
s, d, h = req("POST", f"{BASE}/users/{LIB_ID}/collections", [
    {"key": COLL_KEY, "version": remote_coll_ver, "name": "Stale Batch Collection"}
], H)
test("Stale batch collection failed 412", d.get("failed", {}).get("0", {}).get("code") == 412,
     f"failed={d.get('failed', {})}")
s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/collections/{COLL_KEY}", headers=H)
test("Stale batch collection did not overwrite", d["data"].get("name") == "Remote Collection Wins",
     f"name={d['data'].get('name')}")

s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/searches/{SEARCH_KEY}", headers=H)
remote_search_ver = d["version"]
s, d, h = req("PATCH", f"{BASE}/users/{LIB_ID}/searches/{SEARCH_KEY}",
              {"key": SEARCH_KEY, "version": remote_search_ver, "name": "Remote Search Wins"},
              {**H, "If-Unmodified-Since-Version": str(remote_search_ver)})
test("Remote search update 204", s == 204, f"status={s}")
s, d, h = req("POST", f"{BASE}/users/{LIB_ID}/searches", [
    {"key": SEARCH_KEY, "version": remote_search_ver, "name": "Stale Batch Search", "conditions": []}
], H)
test("Stale batch search failed 412", d.get("failed", {}).get("0", {}).get("code") == 412,
     f"failed={d.get('failed', {})}")
s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/searches/{SEARCH_KEY}", headers=H)
test("Stale batch search did not overwrite", d["data"].get("name") == "Remote Search Wins",
     f"name={d['data'].get('name')}")

print("\n" + "=" * 60)
print("Step 19: 304 Not Modified")
print("=" * 60)
s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/items?format=versions",
              headers={**H, "If-Modified-Since-Version": str(999999)})
try:
    r = urllib.request.Request(
        f"{BASE}/users/{LIB_ID}/items?format=versions",
        headers={**H, "If-Modified-Since-Version": str(999999)}
    )
    resp = urllib.request.urlopen(r)
    test("304 not modified", False, "got 200 instead")
except urllib.error.HTTPError as e:
    test("304 not modified", e.code == 304, f"status={e.code}")

print("\n" + "=" * 60)
print("Step 20: Fulltext and file stubs")
print("=" * 60)
s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/fulltext?since=0", headers=H)
test("Fulltext stub 200", s == 200)
test("Fulltext has Last-Modified-Version", "last-modified-version" in h)

s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/items/{BOOK_KEY}/fulltext", headers=H)
test("Item fulltext 404", s == 404, f"status={s}")

s, d, h = req("GET", f"{BASE}/users/{LIB_ID}/items/{BOOK_KEY}/file", headers=H)
test("File 404", s == 404, f"status={s}")

print("\n" + "=" * 60)
print("Step 21: Schema endpoints")
print("=" * 60)
s, d, _ = req("GET", f"{BASE}/itemTypes", headers=H)
test("Item types list", len(d) > 30)

s, d, _ = req("GET", f"{BASE}/items/new?itemType=book", headers=H)
test("Book template", d.get("itemType") == "book")

print("\n" + "=" * 60)
RESULT = "ALL TESTS PASSED" if failures == 0 else f"{failures} TEST(S) FAILED"
print(f"RESULT: {RESULT}")
print("=" * 60)
sys.exit(1 if failures else 0)
