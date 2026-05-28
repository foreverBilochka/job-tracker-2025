#!/usr/bin/env python3
"""Deploy static files to Vercel via REST API (no CLI needed)."""
import hashlib, os, re, sys, urllib.request, urllib.parse, json

def clean(val, allow=r"[^A-Za-z0-9_\-\.]"):
    """Keep only safe ASCII chars; strip arrows/spaces/UI junk."""
    return re.sub(allow, "", val)

TOKEN      = clean(os.environ["VERCEL_TOKEN"])
PROJECT_ID = clean(os.environ["VERCEL_PROJECT_ID"], r"[^A-Za-z0-9_\-]")
ORG_ID     = clean(os.environ.get("VERCEL_ORG_ID", ""), r"[^A-Za-z0-9_\-]")

print(f"Project ID: {PROJECT_ID[:6]}…")  # show first 6 chars for debug
BASE       = "https://api.vercel.com"
HEADERS    = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

FILES = ["index.html", "vercel.json"]

def api(method, path, body=None, extra_headers=None):
    data = json.dumps(body).encode() if body else None
    headers = {**HEADERS, **(extra_headers or {})}
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"HTTP {e.code}: {err}")
        sys.exit(1)

def upload(path):
    with open(path, "rb") as f:
        content = f.read()
    sha1 = hashlib.sha1(content).hexdigest()
    size = len(content)
    req = urllib.request.Request(
        BASE + "/v2/files",
        data=content,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Length": str(size),
            "x-vercel-digest": sha1,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            r.read()
    except urllib.error.HTTPError as e:
        # 200 or 409 (already exists) are both fine
        if e.code not in (200, 409):
            print(f"Upload {path} failed: HTTP {e.code} {e.read().decode()}")
            sys.exit(1)
    print(f"  uploaded {path} ({size} bytes, sha1={sha1})")
    return {"file": path, "sha": sha1, "size": size}

print("Uploading files...")
file_list = [upload(f) for f in FILES]

params = f"?projectId={PROJECT_ID}"
if ORG_ID:
    params += f"&teamId={ORG_ID}"
url = f"/v13/deployments{params}"

print("Creating deployment...")
result = api("POST", url, {
    "name": "job-tracker",
    "target": "production",
    "files": file_list,
})

if result.get("error"):
    print("Error:", result["error"])
    sys.exit(1)

deploy_url = result.get("url") or result.get("inspectorUrl", "unknown")
print(f"Deployed: https://{deploy_url}")
