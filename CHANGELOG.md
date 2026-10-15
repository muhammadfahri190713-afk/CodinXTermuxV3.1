# Changelog
Format mengikuti Keep a Changelog; versi mengikuti Semantic Versioning.

## [1.4.0] - 2026-10-06
### Ditambahkan
- **Akun lokal**: alur Sign Up/Log in saat pertama jalan (persisten sampai uninstall), pemilihan paket dengan teks
  "There is Max, Pro and Free. Choose your method", `/login` `/logout`.
- **Panel admin lokal** (`!admin_panel` atau `/admin_panel`): IP/lokasi perangkat, akun & riwayat login, pemakaian,
  konfigurasi (rahasia disamarkan) — data LOKAL perangkat ini, bukan dasbor multi-pengguna.
- **`/connect` multi-endpoint**: pilihan cepat Inttelix/OpenRouter/Anthropic/custom, API key wajib sebelum fetch,
  deteksi gaya API (OpenAI-compatible vs Anthropic x-api-key) dengan fallback otomatis antar gaya.
- **Asisten cadangan** opsional, chat-only, aktif hanya bila pengguna mengisi `CODINX_FALLBACK_*` di `.env` lokalnya sendiri.
- Desain utama baru: tema **nova** (bawaan), + obsidian/cyberpunk/sunset/ocean/manus/nova-light (55 tema total),
  preset `manus`, spinner baru, animasi "berpikir" dengan frasa berputar + warna berdenyut mengikuti tema.
- Pencarian web ditulis ulang: parser generik tahan-perubahan-markup + 3 sumber berurutan (DuckDuckGo lite/html, Bing).
- Tab pada baris kosong = ganti mode build/plan cepat.
- Resiliensi tersembunyi: saat endpoint gagal di tengah giliran (umum setelah banyak tool call berurutan) atau
  setelah banyak tool call, id percakapan yang dikirim ke API diganti diam-diam lalu diulang — riwayat/sesi/memori
  yang terlihat user tidak berubah sama sekali, dan tidak ada apa pun yang dicetak kecuali percobaan ulang juga gagal.
### Diperbaiki
- Bug `Session.load()`: id percakapan sempat tidak sinkron dengan id sesi setelah sesi dimuat ulang.
### Keamanan
- Tidak ada API key maupun kredensial nyata yang dibundel ke kode — lihat SECURITY.md.

## [1.3.0] - 2026-10-04
### Ditambahkan
- **Saran live saat mengetik** (ala opencode): `/` memunculkan daftar perintah yang menyempit tiap huruf (`/h` → `/help` teratas); ↑↓ pilih, Tab lengkapi,
  Enter jalankan, Esc tutup; juga untuk argumen, `@file`, dan `$skill`. Editor baris mode-raw tanpa dependensi, jalan di Linux & Termux.
- **Sistem desain**: 49 tema (gelap/terang, aksesibilitas), pemilih tema dengan pratinjau langsung, 10 preset (`/design`), serta `/banner` `/border` `/spinner`
  `/icons` `/prompt` `/gutter` `/footer` `/density`; warna kode mengikuti tema; `/colors` untuk uji terminal.
- Deteksi kedalaman warna (Termux = truecolor), latar terang/gelap otomatis (OSC 11 / COLORFGBG), kontras tiap tema dijamin (WCAG).
- Penampil Markdown `/docs` & `/view` (markdown-it); ekspor tabel ke .yaml/.html/.rst/.tex/.txt; skrip `yamlpp.py`.
- Termux: tanpa root, pembungkus installer, zona waktu offline (tzdata vendor), ID brankas per-instalasi, kamera via Termux:API, `$TMPDIR`.
### Diperbaiki
- UI tampak abu-abu: garis/judul/kode/footer kini memakai peran warna sendiri, bukan satu warna redup; pemetaan 256/16 warna diperbaiki.
- Riwayat input tidak lagi ditimpa readline saat editor baru dipakai.
- `vendor_pygments.py` tidak lagi menghapus pustaka vendor lain.

## [1.2.0] - 2026-10-02
### Ditambahkan
- **Diagnosa proxy otomatis** (`/doctor`): mendeteksi apakah proxy meneruskan riwayat percakapan dan apakah tool bisa dipanggil;
  mode `flat` (riwayat digabung satu pesan) dan mode tool `text` (`<tool_call>`) untuk gateway yang tidak mendukungnya.
- **Skills bisa dijalankan langsung**: `/skills`, `/skill <nama>`, `/<nama>`, `$nama` di pesan; pencocokan skill otomatis. 42 skill bawaan (sysadmin, dev, keamanan).
- **Memori**: penangkapan otomatis ("ingat bahwa…", "nama saya…"), `/remember`, `/forget`, tanpa duplikat.
- Syntax highlighting (Pygments disertakan), tabel yang membungkus teks, `/diff`.
- Hooks (PreToolUse/PostToolUse/UserPromptSubmit/Stop), klien MCP (stdio), sub-agent khusus (6 bawaan), tool `websearch` dan `multiedit`.
- Konfigurasi proyek `.codinx/config.json` (kunci terbatas), log debug (`CODINX_DEBUG=1`, `/debug`, `codinx logs`), dukungan `.env`.
- Suite test (`make test`), CI GitHub Actions, pemindai rahasia + pre-commit hook, completions bash/zsh, Dockerfile.
- **Mode uji coba** (bawaan aktif): semua 170 model gratis — tanpa kunci paket/trial terbatas dan Dinar tidak dipotong. Matikan: `CODINX_TRIAL=0`.
### Diperbaiki
- Nilai dari env/`.env` tidak lagi ikut tersimpan permanen ke `config.json`; `load()` memakai salinan dalam (dict bersarang tidak dipakai bersama).
- Agent lupa percakapan pada gateway yang hanya membaca pesan terakhir / menolak role `tool`.
- Skill tidak bisa dijalankan pada proxy tanpa function-calling.
- Tabel memotong teks panjang; penangkapan nama menyimpan kata tambahan.

## [1.0.0] - 2026-09-30
- Rilis awal: agent terminal root-only, izin Iya/Tidak/Selalu, tier FREE/PRO/MAX + Dinar, sesi, memori, skills, tema.
