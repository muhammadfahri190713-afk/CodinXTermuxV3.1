"""Asisten cadangan bawaan CodinX ("GPT 5.6 Sol") — aktif hanya bila pengguna mengisi sendiri CODINX_FALLBACK_*
di .env/api.py lokal (lihat .env.example). TIDAK ada API key yang dibawa oleh CodinX: kunci nyata tidak pernah
disertakan di kode yang dibagikan/di-commit (lihat SECURITY.md). Bersifat chat-only — tidak bisa menjalankan
tool atau perintah apa pun di perangkatmu, hanya membantu menjawab.
"""
from . import api, config

NAME = "GPT 5.6 Sol"
IDENTITY = (
    "Kamu adalah GPT 5.6 Sol, asisten cadangan bawaan CodinX. Kamu HANYA mengobrol dan menjawab pertanyaan — "
    "kamu tidak bisa menjalankan tool, perintah, atau menyentuh file apa pun di perangkat user. Jika ditanya "
    "siapa dirimu, jawab sebagai GPT 5.6 Sol, asisten cadangan CodinX, dengan jujur dan singkat. Jawab dalam "
    "bahasa yang dipakai user."
)


def active_config():
    base = config.env("CODINX_FALLBACK_BASE_URL")
    key = config.env("CODINX_FALLBACK_API_KEY")
    model = config.env("CODINX_FALLBACK_MODEL") or "gpt-5.6-sol"
    if not (base and key):
        return None
    return {"base_url": config.normalize_url(base), "model": model, "_key": key}


def available():
    return active_config() is not None


def ask(user_text, timeout=90):
    """-> teks balasan, atau mengangkat api.ApiError bila cadangan juga gagal."""
    cfg = active_config()
    if not cfg:
        raise api.ApiError("Asisten cadangan belum dikonfigurasi (CODINX_FALLBACK_BASE_URL/API_KEY).")
    msgs = [{"role": "system", "content": IDENTITY}, {"role": "user", "content": user_text}]
    msg, _usage, _meta = api.chat(cfg, cfg["_key"], msgs, tools=None, timeout=timeout)
    return msg.get("content") or "(tidak ada jawaban)"
