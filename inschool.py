"""Minimal read-only client for Visma InSchool: reuses the browser session saved by login.mjs."""
import json
import os
import pathlib
import ssl
import urllib.error
import urllib.request

SESSION_FILE = pathlib.Path(os.environ.get("INSCHOOL_SESSION", pathlib.Path.home() / ".visma-inschool-session.json"))
# python.org builds of Python on macOS don't see the system certificates, so use the system bundle when it exists
CAFILE = "/etc/ssl/cert.pem"
SSL_CTX = ssl.create_default_context(cafile=CAFILE if os.path.exists(CAFILE) else None)
LOGIN_HINT = "log in again: node login.mjs <your-school>.inschool.visma.no"


class AuthError(Exception):
    pass


def load_session():
    if not SESSION_FILE.exists():
        raise AuthError(f"no session file {SESSION_FILE}; {LOGIN_HINT}")
    return json.loads(SESSION_FILE.read_text())


def host():
    return os.environ.get("INSCHOOL_HOST") or load_session()["host"]


def update_cookies(headers):
    """The Authorization cookie lives ~5 minutes; the server sends a fresh one in Set-Cookie, so keep it."""
    fresh = {}
    for h in headers.get_all("Set-Cookie") or []:
        name, _, rest = h.partition("=")
        fresh[name.strip()] = rest.split(";", 1)[0]
    if not fresh:
        return
    sess = load_session()
    for c in sess["cookies"]:
        if c["name"] in fresh:
            c["value"] = fresh.pop(c["name"])
    sess["cookies"] += [{"name": k, "value": v, "domain": host(), "path": "/", "expires": -1} for k, v in fresh.items()]
    SESSION_FILE.write_text(json.dumps(sess, indent=1))
    SESSION_FILE.chmod(0o600)


def get(path):
    """GET https://<host>/control/... and return parsed JSON."""
    cookies = "; ".join(f"{c['name']}={c['value']}" for c in load_session()["cookies"])
    req = urllib.request.Request(f"https://{host()}{path}", headers={
        "Cookie": cookies, "Accept": "application/json", "X-Requested-With": "XMLHttpRequest",
    })
    try:
        with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as r:
            update_cookies(r.headers)
            raw = r.read()
            if "json" not in r.headers.get("Content-Type", ""):
                raise AuthError("InSchool returned the login page instead of data")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise AuthError(f"InSchool answered {e.code}, the session has expired; {LOGIN_HINT}") from e
        raise
    except AuthError as e:
        raise AuthError(f"{e}; {LOGIN_HINT}") from e
