#!/usr/bin/env python3
"""Generic App Store Connect API client (reads ~/.config/appstoreconnect/config.json).

Requires: a venv with  pyjwt cryptography requests
Usage:
  python asc-api.py diag <appId>
  python asc-api.py groups <appId>
  python asc-api.py add-build <groupId> <buildId>
  python asc-api.py add-tester <groupId> <testerId>
  python asc-api.py invite <appId> <testerId>
  python asc-api.py new-internal-group <appId> <name>
Read the IDs with `diag`/`groups`.
"""
import os, sys, time, json
import jwt as pyjwt
import requests

CFG_DIR = os.path.expanduser("~/.config/appstoreconnect")
CFG = json.load(open(os.path.join(CFG_DIR, "config.json")))
PRIVATE_KEY = open(os.path.join(CFG_DIR, CFG["p8"])).read()
BASE = "https://api.appstoreconnect.apple.com"

def token():
    n = int(time.time())
    return pyjwt.encode({"iss": CFG["issuerId"], "iat": n, "exp": n + 1000, "aud": "appstoreconnect-v1"},
                        PRIVATE_KEY, algorithm="ES256", headers={"kid": CFG["keyId"], "typ": "JWT"})

def req(method, path, retry=True, **kw):
    for i in range(6 if retry else 1):
        r = requests.request(method, BASE + path,
                             headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json"},
                             timeout=25, **kw)
        if r.status_code < 500:
            return r
        print(f"  (apple {r.status_code}, retry {i+1})"); time.sleep(3 + i * 2)
    return r

def get(path):
    r = req("GET", path)
    if r.status_code >= 400:
        print(f"  !{r.status_code} {path}: {r.text[:150]}"); return None
    return r.json()

def diag(app):
    a = get(f"/v1/apps/{app}")
    if a: print("APP:", a["data"]["attributes"].get("name"), a["data"]["attributes"].get("bundleId"))
    b = get(f"/v1/builds?filter[app]={app}&limit=6&sort=-version")
    for d in (b["data"] if b else []):
        at = d["attributes"]
        bd = get(f"/v1/builds/{d['id']}/buildBetaDetail")
        st = bd["data"]["attributes"].get("internalBuildState") if bd else "?"
        print(f"  build {at['version']} | {at['processingState']} | internal={st} | id={d['id']}")
    g = get(f"/v1/apps/{app}/betaGroups")
    for d in (g["data"] if g else []):
        at = d["attributes"]; print(f"  group '{at['name']}' internal={at['isInternalGroup']} id={d['id']}")
        t = get(f"/v1/betaGroups/{d['id']}/betaTesters")
        if t: print("     testers:", [(x['attributes'].get('email'), x['attributes'].get('state')) for x in t['data']])

def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    cmd = sys.argv[1]
    if cmd == "diag":
        diag(sys.argv[2])
    elif cmd == "groups":
        g = get(f"/v1/apps/{sys.argv[2]}/betaGroups")
        for d in (g["data"] if g else []):
            print(d["attributes"]["name"], d["attributes"]["isInternalGroup"], d["id"])
    elif cmd == "add-build":
        r = req("POST", f"/v1/betaGroups/{sys.argv[2]}/relationships/builds",
                json={"data": [{"type": "builds", "id": sys.argv[3]}]})
        print("add-build ->", r.status_code, r.text[:150] if r.status_code >= 400 else "OK")
    elif cmd == "add-tester":
        r = req("POST", f"/v1/betaGroups/{sys.argv[2]}/relationships/betaTesters",
                json={"data": [{"type": "betaTesters", "id": sys.argv[3]}]})
        print("add-tester ->", r.status_code, r.text[:150] if r.status_code >= 400 else "OK")
    elif cmd == "invite":
        r = req("POST", "/v1/betaTesterInvitations",
                json={"data": {"type": "betaTesterInvitations", "relationships": {
                    "betaTester": {"data": {"type": "betaTesters", "id": sys.argv[3]}},
                    "app": {"data": {"type": "apps", "id": sys.argv[2]}}}}})
        print("invite ->", r.status_code, "OK sent" if r.status_code < 400 else r.text[:200])
    elif cmd == "new-internal-group":
        r = req("POST", "/v1/betaGroups", json={"data": {"type": "betaGroups",
                "attributes": {"name": sys.argv[3], "isInternalGroup": True},
                "relationships": {"app": {"data": {"type": "apps", "id": sys.argv[2]}}}}})
        print("new-group ->", r.status_code, (r.json()["data"]["id"] if r.status_code < 400 else r.text[:200]))
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
