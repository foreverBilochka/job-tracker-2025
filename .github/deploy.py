#!/usr/bin/env python3
"""Deploy static files to Vercel via REST API (no CLI needed)."""
import hashlib, os, sys, urllib.request, json

TOKEN      = os.environ["VERCEL_TOKEN"].strip()
PROJECT_ID = os.environ["VERCEL_PROJECT_ID"].strip()
ORG_ID     = os.environ.get("VERCEL_ORG_ID", "").strip()
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

url = f"/v13/deployments"
if ORG_ID:
    url += f"?teamId={ORG_ID}"

print("Creating deployment...")
result = api("POST", url, {
    "projectId": PROJECT_ID,
    "target": "production",
    "files": file_list,
})

if result.get("error"):
    print("Error:", result["error"])
    sys.exit(1)

deploy_url = result.get("url") or result.get("inspectorUrl", "unknown")
print(f"Deployed: https://{deploy_url}")
