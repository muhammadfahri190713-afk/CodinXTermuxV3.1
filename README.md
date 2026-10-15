<div align="center">

# CodinX

### Terminal-native coding agent untuk Linux & Termux

**Menulis · Menjalankan · Memahami · Memverifikasi kode — langsung dari terminal.**

[![CI](https://github.com/muhammadfahri190713-afk/CodinXTermuxV3.1/actions/workflows/ci.yml/badge.svg)](https://github.com/muhammadfahri190713-afk/CodinXTermuxV3.1/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Termux](https://img.shields.io/badge/Termux-ready-000000?style=flat-square&logo=android&logoColor=white)](docs/TERMUX.md)
[![Standard library](https://img.shields.io/badge/dependencies-stdlib%20%2B%20vendored-64748b?style=flat-square)](THIRD_PARTY_NOTICES.md)

[**Mulai cepat**](#-mulai-cepat) · [**Fitur**](#-fitur-unggulan) · [**Dokumentasi**](#-dokumentasi) · [**Kontribusi**](#-kontribusi)

</div>

---

## Tentang CodinX

CodinX adalah coding agent berbasis terminal yang dirancang untuk alur kerja developer yang cepat, transparan, dan tetap berada di bawah kendali pengguna. Ia menggabungkan chat dengan model, tool untuk bekerja pada workspace, permission gate, sesi yang dapat dilanjutkan, skills, sub-agent, serta dukungan MCP dalam satu antarmuka terminal.

> Dibuat untuk developer yang ingin AI membantu mengerjakan kode tanpa kehilangan visibilitas atas apa yang dibaca, ditulis, dan dijalankan.

Berjalan **tanpa root** di Linux, container, dan **Termux**. CodinX ditulis dengan Python dan memanfaatkan standard library dengan komponen yang sudah di-vendor agar instalasi tetap sederhana.

## Mengapa CodinX?

| Prinsip | Implementasi |
|---|---|
| **Terminal-first** | Cocok untuk SSH, server, container, dan workflow keyboard-centric. |
| **Aman secara default** | Permission gate, pemblokiran perintah destruktif, secret scanner, dan log debug terpisah. |
| **Tahan terhadap proxy** | Diagnosis kompatibilitas otomatis untuk history, tool-calling, dan mode fallback. |
| **Bisa dilanjutkan** | Sesi, memori, `/undo`, `/redo`, `/diff`, dan compact context membantu pekerjaan panjang. |
| **Ekstensibel** | 42 skills, 6 sub-agent bawaan, hooks, MCP server, tema, dan command yang dapat dikembangkan. |
| **Mobile-friendly** | Dirancang untuk layar sempit dan instalasi tanpa root di Termux. |

## ✨ Fitur unggulan

- **Live command suggestions** — ketik `/`, `@file`, atau `$skill` untuk autocomplete interaktif.
- **17 tools** — read, write, edit, multiedit, list, glob, grep, bash/background, webfetch, websearch, todo, task, skill, memory, table, camera, dan MCP.
- **42 skills siap pakai** — jalankan lewat `/skills`, `/skill <nama>`, `/<nama>`, atau `$nama`.
- **Terminal UI yang dapat dikustomisasi** — 49 tema, 10 preset desain, banner, border, spinner, ikon, dan prompt.
- **Permission gate** — aksi sensitif meminta izin; aksi destruktif diblokir secara default.
- **Session & memory** — lanjutkan percakapan, simpan konteks, dan kelola memori jangka panjang.
- **Proxy compatibility layer** — fallback untuk gateway yang tidak sepenuhnya mendukung OpenAI-compatible API atau function calling.
- **MCP & sub-agent** — perluas kemampuan CodinX dengan server dan agent khusus.
- **Markdown & syntax highlighting** — output nyaman dibaca langsung di terminal.

## 🚀 Mulai cepat

### 1. Siapkan proyek

```bash
git clone https://github.com/muhammadfahri190713-afk/CodinXTermuxV3.1.git
cd CodinXTermuxV3.1
```

### 2. Siapkan konfigurasi API

```bash
cp api.example.py api.py
# Edit api.py, lalu isi API_KEY milikmu.
```

`api.py` dan `.env` sudah masuk `.gitignore` sehingga key lokal tidak ikut ter-commit.

### 3. Jalankan CodinX

```bash
# Tanpa instalasi permanen
python3 bin/codinx

# Atau melalui npm script
npm run -s codinx-agents

# Instal command `codinx` secara permanen
bash install.sh
```

Contoh mode non-interaktif:

```bash
codinx run "buat web todo sederhana" --auto
codinx run -c "lanjutkan pekerjaan terakhir"
codinx run "/skill debug-fix error x"
codinx run "jelaskan struktur proyek ini" --format json
```

> **Termux:** jalankan `bash install.sh`; installer akan memakai `$PREFIX` secara otomatis dan tidak membutuhkan root. Panduan lengkap tersedia di [docs/TERMUX.md](docs/TERMUX.md).

## 🔐 Keamanan & konfigurasi

Sebelum commit atau push, jalankan:

```bash
python3 scripts/secret_scan.py .
```

Untuk daftar variabel environment, endpoint, mode trial, dan pengaturan lanjutan, baca [docs/CONFIG.md](docs/CONFIG.md). Jangan pernah meng-commit API key, `.env`, `api.py`, atau file kredensial lain.

Pada masa uji coba, `trial_mode` aktif secara default. Untuk kembali ke aturan paket normal:

```bash
export CODINX_TRIAL=0
```

## 📚 Dokumentasi

| Topik | Panduan |
|---|---|
| Arsitektur | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Perintah lengkap | [docs/COMMANDS.md](docs/COMMANDS.md) |
| Konfigurasi & environment | [docs/CONFIG.md](docs/CONFIG.md) |
| Kompatibilitas proxy | [docs/PROXY_COMPAT.md](docs/PROXY_COMPAT.md) |
| Permission system | [docs/PERMISSIONS.md](docs/PERMISSIONS.md) |
| Tema & desain terminal | [docs/DESIGN.md](docs/DESIGN.md) |
| Linux & Termux | [docs/TERMUX.md](docs/TERMUX.md) |
| Skills | [docs/SKILLS.md](docs/SKILLS.md) |
| Sub-agent | [docs/SUBAGENTS.md](docs/SUBAGENTS.md) |
| Hooks | [docs/HOOKS.md](docs/HOOKS.md) |
| MCP | [docs/MCP.md](docs/MCP.md) |
| Troubleshooting | [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) |
| Publish & security checklist | [docs/GITHUB.md](docs/GITHUB.md) · [SECURITY.md](SECURITY.md) |

## 🧪 Pengembangan

```bash
make test    # jalankan seluruh test suite
make scan    # audit secret sebelum push
make docs    # regenerasi dokumentasi dari kode
make zip     # buat distribusi di dist/CodinX.zip
```

CI GitHub Actions menjalankan test pada Python 3.9, 3.10, 3.11, dan 3.12 sekaligus melakukan secret scan pada setiap push dan pull request.

## 🤝 Kontribusi

Ide, laporan bug, dokumentasi, dan pull request sangat diterima. Silakan baca [CONTRIBUTING.md](CONTRIBUTING.md) sebelum mulai, gunakan issue template yang tersedia, dan sertakan langkah reproduksi untuk laporan bug.

## 📄 Lisensi & pihak ketiga

CodinX dirilis di bawah [MIT License](LICENSE). Komponen pihak ketiga yang di-vendor dan lisensinya tercantum di [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

<div align="center">

**Bangun lebih cepat. Tetap paham apa yang terjadi.**

</div>
