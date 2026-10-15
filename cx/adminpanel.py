"""Panel admin lokal — rahasia setara .env/api.py, akses lewat `!admin_panel`.

PENTING (dibaca jujur): CodinX berjalan lokal di perangkatmu sendiri tanpa server pusat. Panel ini HANYA bisa
menunjukkan data dari perangkat ini (akun yang dibuat di sini, riwayat login di sini, IP publik perangkat ini).
Tidak ada data dari instalasi CodinX orang lain yang mengalir ke sini — tidak ada backend yang mengumpulkannya.
"""
import os
import time

from . import auth, config, envinfo, geo, hooks, mcp, skills, tiers
from .session import Session


def _mask_url(url):
    return url or "(belum diatur)"


def _mask_key(cfg):
    src = config.key_source()
    key = config.get_key()
    return f"{src}" + (f"  ({key[:4]}…{len(key)} char)" if key else "  (kosong)")


def _fmt_ts(ts):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts)) if ts else "-"


def build(cfg, session, cwd):
    g = geo.lookup()
    ad = auth.admin_data()
    st = tiers.status(cfg)
    sessions = Session.list_all()
    sections = []

    sections.append(("Perangkat & jaringan", ["", ""], [
        ["IP publik", g.get("ip") or "(tidak terdeteksi)"],
        ["Lokasi", ", ".join(x for x in (g.get("city"), g.get("province"), g.get("country")) if x) or "-"],
        ["Zona waktu", geo.tz_name(cfg)],
        ["Platform", envinfo.platform_label()],
        ["Folder kerja", cwd],
        ["Sumber lokasi", g.get("source", "-")],
    ]))

    sections.append(("Akun lokal perangkat ini", ["user", "dibuat", "login terakhir", "jml login"],
                     [[u["username"], _fmt_ts(u["created"]), _fmt_ts(u["last_login"]), u["login_count"]] for u in ad["users"]] or
                     [["(belum ada akun)", "", "", ""]]))

    sections.append((f"Riwayat login/aktivitas ({len(ad['events'])}/{ad['total_events']} terakhir)",
                     ["waktu", "user", "aksi", "status", "ip", "lokasi"],
                     [[_fmt_ts(e["ts"]), e["username"], e["action"], "✓" if e["ok"] else "✗", e["ip"] or "-", e["location"] or "-"]
                      for e in ad["events"]] or [["-", "-", "-", "-", "-", "-"]]))

    sections.append(("Sesi & pemakaian", ["", ""], [
        ["user aktif", ad["current"] or "(tidak ada)"],
        ["total sesi tersimpan", len(sessions)],
        ["pesan di sesi ini", len(session.messages)],
        ["token terpakai (sesi ini)", session.tokens_total],
        ["paket", "trial (semua gratis)" if st["trial"] else st["tier"]],
        ["Dinar hari ini", f"{st['dinar']}/{st['limit']}" if not st["trial"] else "-"],
    ]))

    sections.append(("Konfigurasi (rahasia disamarkan)", ["", ""], [
        ["model aktif", cfg.get("model", "-")],
        ["endpoint", _mask_url(cfg.get("base_url"))],
        ["sumber API key", _mask_key(cfg)],
        ["tema/desain", f"{cfg.get('theme', 'auto')} / " + ",".join(f"{k}={v}" for k, v in (cfg.get("design") or {}).items())[:60]],
        ["asisten cadangan", "aktif" if __import__("cx.fallback", fromlist=["x"]).available() else "tidak dikonfigurasi"],
    ]))

    h = hooks.load(cwd, cfg)
    n_hooks = sum(len(v) for v in h.values())
    sections.append(("Ekstensi", ["", ""], [
        ["hooks aktif", n_hooks],
        ["server MCP terdaftar", len(mcp.manager.specs)],
        ["skills tersedia", len(skills.discover(cwd))],
    ]))
    return sections


def show(ui_, cfg, session, cwd):
    from .themes import c
    ui_.p()
    ui_.p(c("heading", "▌ PANEL ADMIN — data lokal perangkat ini", bold=True))
    ui_.p(c("muted", "  Tidak ada server pusat: hanya menampilkan data dari instalasi CodinX ini."))
    for title, cols, rows in build(cfg, session, cwd):
        ui_.table(cols, rows, title)
    ui_.p()
