"""Profil koneksi untuk /connect: deteksi gaya API per endpoint (OpenAI-compatible vs Anthropic native) supaya
daftar model bisa diambil lewat HTTP dari endpoint APA PUN — Inttelix, OpenRouter, Anthropic, atau proxy custom.

Chat tetap memakai bentuk OpenAI-compatible (cx/api.py): cocok untuk Inttelix, OpenRouter, dan kebanyakan proxy
(termasuk endpoint cadangan GPT 5.6 Sol — path-nya sendiri berakhiran /chat/completions). Endpoint Anthropic asli
hanya didukung untuk DAFTAR MODEL di sini; chat native Anthropic (bentuk pesan berbeda) belum diimplementasikan.
"""
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

ANTHROPIC_VERSION = "2023-06-01"

KNOWN = {
    "inttelix.vercel.app": ("Inttelix", "openai"),
    "openrouter.ai": ("OpenRouter", "openai"),
    "api.anthropic.com": ("Anthropic", "anthropic"),
    "api.manus.im": ("Manus", "openai"),
    "api.openai.com": ("OpenAI", "openai"),
    "api.groq.com": ("Groq", "openai"),
    "api.together.xyz": ("Together AI", "openai"),
    "api.deepseek.com": ("DeepSeek", "openai"),
}
QUICK_PICKS = [("inttelix", "https://inttelix.vercel.app/api/v1", "bawaan CodinX"),
               ("openrouter", "https://openrouter.ai/api/v1", "ratusan model, satu key"),
               ("anthropic", "https://api.anthropic.com", "API resmi Anthropic (hanya daftar model)"),
               ("custom", "", "endpoint lain / proxy milikmu sendiri")]


class ConnectError(Exception):
    def __init__(self, msg, attempts=None):
        super().__init__(msg)
        self.attempts = attempts or []


def label_for(base_url):
    host = urllib.parse.urlparse(base_url).netloc.lower()
    for dom, (name, _) in KNOWN.items():
        if dom in host:
            return name
    return host or "custom"


def style_for(base_url):
    host = urllib.parse.urlparse(base_url).netloc.lower()
    for dom, (_, style) in KNOWN.items():
        if dom in host:
            return style
    return "openai"


def _ctx(insecure):
    if not insecure:
        return None
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def _get(url, headers, timeout, insecure):
    req = urllib.request.Request(url, method="GET")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx(insecure)) as r:
        return json.loads(r.read().decode())


def _ids_from_openai(obj):
    items = obj.get("data", obj) if isinstance(obj, dict) else obj
    return sorted({(m.get("id") if isinstance(m, dict) else str(m)) for m in items if m})


def _ids_from_anthropic(obj):
    return sorted({m["id"] for m in obj.get("data", []) if m.get("id")})


def _try_openai(base_url, key, timeout, insecure):
    url = base_url.rstrip("/")
    if not url.endswith(("/models",)):
        url += "/models"
    obj = _get(url, {"Authorization": "Bearer " + key, "User-Agent": "CodinX/1.4"}, timeout, insecure)
    return _ids_from_openai(obj)


def _try_anthropic(base_url, key, timeout, insecure):
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3]
    obj = _get(root + "/v1/models", {"x-api-key": key, "anthropic-version": ANTHROPIC_VERSION, "User-Agent": "CodinX/1.4"}, timeout, insecure)
    return _ids_from_anthropic(obj)


def list_models(base_url, key, style=None, timeout=20, insecure=False):
    """-> (ids, style_used).  Coba gaya yang terdeteksi dulu, lalu gaya lain sebagai cadangan."""
    order = [style or style_for(base_url)]
    order += [s for s in ("openai", "anthropic") if s not in order]
    attempts = []
    for s in order:
        try:
            fn = _try_openai if s == "openai" else _try_anthropic
            ids = fn(base_url, key, timeout, insecure)
            if ids:
                return ids, s
            attempts.append(f"{s}: 0 model dikembalikan")
        except urllib.error.HTTPError as e:
            attempts.append(f"{s}: HTTP {e.code}")
        except urllib.error.URLError as e:
            attempts.append(f"{s}: {getattr(e, 'reason', e)}")
        except (ValueError, KeyError, TypeError) as e:
            attempts.append(f"{s}: respons tak terduga ({type(e).__name__})")
    raise ConnectError("Gagal mengambil daftar model dari semua gaya API yang dicoba.", attempts)
