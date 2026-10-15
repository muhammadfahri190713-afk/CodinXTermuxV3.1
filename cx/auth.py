"""Akun lokal (Sign Up / Log in) — khusus perangkat ini, tersimpan selamanya sampai diinstal ulang.

Setara rahasia seperti .env/api.py: file di ~/.codinx/auth.json (mode 600), tidak pernah ikut ter-commit
(folder .codinx/ sudah di .gitignore). Password di-hash (PBKDF2-HMAC-SHA256 + salt per-user) — tidak pernah
disimpan apa adanya. Admin panel (!admin_panel) membaca ringkasan data ini.
"""
import hashlib
import hmac
import json
import os
import re
import time

from . import config, geo

FILE = os.path.join(config.HOME, "auth.json")
ITER = 200_000
MAX_EVENTS = 500


def _empty():
    return {"users": {}, "events": [], "current": None}


def load():
    try:
        with open(FILE, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return _empty()
    d.setdefault("users", {})
    d.setdefault("events", [])
    d.setdefault("current", None)
    return d


def _save(d):
    config.ensure_dirs()
    d["events"] = d["events"][-MAX_EVENTS:]
    tmp = FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.chmod(tmp, 0o600)
    os.replace(tmp, FILE)


def _hash(password, salt_hex):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), ITER).hex()


def _client_info():
    g = geo.lookup()
    return {"ip": g.get("ip", "") or "", "location": ", ".join(x for x in (g.get("city"), g.get("province"), g.get("country")) if x)}


def _event(d, username, action, ok=True, note=""):
    info = _client_info()
    d["events"].append({"ts": time.time(), "username": username, "action": action, "ok": ok,
                        "ip": info["ip"], "location": info["location"], "note": note})


VALID_NAME = re.compile(r"^[A-Za-z0-9_.-]{3,24}$")


def signup(username, password):
    username = (username or "").strip()
    if not VALID_NAME.match(username):
        return False, "Nama pengguna 3-24 karakter: huruf, angka, titik, strip, underscore."
    if len(password or "") < 4:
        return False, "Password minimal 4 karakter."
    d = load()
    key = username.lower()
    if key in d["users"]:
        return False, f"'{username}' sudah terdaftar di perangkat ini. Pakai /login atau pilih Log in."
    salt = os.urandom(16).hex()
    now = time.time()
    d["users"][key] = {"username": username, "salt": salt, "hash": _hash(password, salt),
                       "created": now, "last_login": now, "login_count": 1}
    d["current"] = username
    _event(d, username, "signup")
    _event(d, username, "login")
    _save(d)
    return True, f"Akun '{username}' dibuat dan masuk."


def login(username, password):
    username = (username or "").strip()
    d = load()
    key = username.lower()
    u = d["users"].get(key)
    if not u or not hmac.compare_digest(_hash(password, u["salt"]), u["hash"]):
        _event(d, username or "(?)", "login", ok=False)
        _save(d)
        return False, "Nama pengguna atau password salah."
    u["last_login"] = time.time()
    u["login_count"] = u.get("login_count", 0) + 1
    d["current"] = u["username"]
    _event(d, u["username"], "login")
    _save(d)
    return True, f"Selamat datang kembali, {u['username']}."


def logout():
    d = load()
    who = d.get("current")
    if who:
        _event(d, who, "logout")
    d["current"] = None
    _save(d)
    return who


def current_user():
    return load().get("current")


def has_any_account():
    return bool(load()["users"])


def admin_data(limit_events=20):
    d = load()
    users = [{"username": u["username"], "created": u["created"], "last_login": u["last_login"], "login_count": u["login_count"]}
             for u in sorted(d["users"].values(), key=lambda x: -x["created"])]
    events = list(reversed(d["events"][-limit_events:]))
    return {"users": users, "events": events, "current": d.get("current"), "total_events": len(d["events"])}
