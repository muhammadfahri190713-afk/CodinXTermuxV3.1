"""Uji integrasi di TERMINAL SUNGGUHAN (pty): popup saran muncul live, Tab/Enter/Esc bekerja, menu tema dengan pratinjau."""
import os
import re
import select
import sys
import tempfile
import time
import unittest

from . import ROOT, mock_proxy

try:
    import pty
except ImportError:                                         # pragma: no cover
    pty = None


class Pty:
    def __init__(self, env_extra=None, cols=60, rows=24):
        self.home = tempfile.mkdtemp()
        self.cwd = tempfile.mkdtemp()
        self.srv, port = mock_proxy.start()
        env = {k: v for k, v in os.environ.items() if not k.startswith(("CODINX_", "NO_COLOR"))}
        env.update(HOME=self.home, TERM="xterm-256color", COLUMNS=str(cols), LINES=str(rows), TERMUX_VERSION="0.118",
                   CODINX_BASE_URL=f"http://127.0.0.1:{port}/v1", CODINX_API_KEY="k", CODINX_MODEL="m-full",
                   CODINX_AUTO_PROBE="0", CODINX_NO_BGQUERY="1")
        env.update(env_extra or {})
        code = f"import sys; sys.path.insert(0, {ROOT!r}); from cx.cli import main; sys.exit(main([]))"
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.chdir(self.cwd)
            os.execvpe(sys.executable, [sys.executable, "-c", code], env)
        self.buf = b""
        self.pump(2.0)

    def signup(self, user="tester", pw="testpass", plan="3"):
        """Lewati gerbang masuk akun sekali di awal (Sign Up) + pilihan paket, lalu bersihkan buffer."""
        self.send("1\r", 0.6)
        self.send(user + "\r", 0.6)
        self.send(pw + "\r", 0.8)
        self.send(plan + "\r", 1.2)
        self.buf = b""

    def plain(self):
        return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", self.buf.decode("utf-8", "replace")).replace("\r", "")

    def pump(self, t):
        end = time.time() + t
        while time.time() < end:
            r, _, _ = select.select([self.fd], [], [], 0.05)
            if r:
                try:
                    d = os.read(self.fd, 65536)
                except OSError:
                    return
                if not d:
                    return
                self.buf += d

    def send(self, data, wait=0.45):
        mark = len(self.buf)
        os.write(self.fd, data if isinstance(data, bytes) else data.encode())
        self.pump(wait)
        return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", self.buf[mark:].decode("utf-8", "replace")).replace("\r", "")

    def close(self):
        try:
            os.write(self.fd, b"\x15/exit\r")
            self.pump(0.8)
            os.close(self.fd)
        except OSError:
            pass
        try:
            os.waitpid(self.pid, 0)
        except ChildProcessError:
            pass
        self.srv.shutdown()
        self.srv.server_close()


@unittest.skipUnless(pty and os.name == "posix", "butuh pty (POSIX)")
class LivePopup(unittest.TestCase):
    def setUp(self):
        self.t = Pty()
        self.t.signup()
        self.addCleanup(self.t.close)

    def test_slash_shows_list_and_h_puts_help_first(self):
        out = self.t.send("/")
        for needle in ("/help", "/new", "/sessions", "Tab"):
            self.assertIn(needle, out)
        out = self.t.send("h")
        self.assertIn("/help", out)
        self.assertLess(out.find("/help"), out.find("/historymode") if "/historymode" in out else 10 ** 9)

    def test_every_letter_narrows_the_list(self):
        self.t.send("/")
        out = self.t.send("t")
        self.assertIn("/theme", out)
        out = self.t.send("h")
        self.assertIn("/theme", out)
        self.assertNotIn("/sessions", out)

    def test_tab_completes_and_shows_argument_suggestions(self):
        self.t.send("/th")
        out = self.t.send("\t")
        self.assertIn("/theme", out)
        self.assertTrue("auto" in out and "dark" in out, out)               # saran argumen langsung setelah /theme␠
        out = self.t.send("tok")
        self.assertIn("tokyonight", out)

    def test_enter_runs_highlighted_command(self):
        out = self.t.send("/hel\r", wait=1.2)
        self.assertTrue("perintah" in out and "fungsi" in out, out[-300:])

    def test_escape_closes_popup_and_arrow_navigation_runs_other_command(self):
        self.t.send("/h")
        self.t.send("\x1b", wait=0.5)
        self.t.send("\x15")
        self.t.send("/h")
        out = self.t.send("\x1b[B\r", wait=1.0)                           # ↓ lalu Enter -> butir kedua (/hooks)
        self.assertIn("/hooks", out)
        self.assertIn("hooks", out.lower().split("/hooks", 1)[1])               # perintahnya benar-benar dijalankan

    def test_at_file_suggestions(self):
        os.makedirs(os.path.join(self.t.cwd, "src"))
        open(os.path.join(self.t.cwd, "src", "app.py"), "w").close()
        open(os.path.join(self.t.cwd, "catatan.txt"), "w").close()
        out = self.t.send("lihat @")
        self.assertTrue("src/" in out and "catatan.txt" in out, out)
        self.assertNotIn("@src/app.py", out)

    def test_theme_picker_with_live_preview_and_apply(self):
        out = self.t.send("/theme\r", wait=1.5)
        self.assertIn("Tema", out)
        self.assertIn("auto", out)
        self.assertIn("Judul", out)                                      # pratinjau tampil
        out = self.t.send("dracula", wait=0.8)
        self.assertIn("dracula", out)
        out = self.t.send("\r", wait=1.0)
        self.assertIn("Tema: dracula", out)
        self.t.send("\x15")
        out = self.t.send("/design show\r", wait=1.0)
        self.assertIn("dracula", out)

    def test_design_command_changes_ui(self):
        out = self.t.send("/design retro\r", wait=1.2)
        self.assertIn("Desain: retro", out)
        self.assertIn("╔", out)                                           # border ganda pada banner
        out = self.t.send("/colors\r", wait=1.0)
        self.assertIn("truecolor", out)                                  # Termux terdeteksi

    def test_unicode_and_wrapping_input_stays_on_one_row(self):
        self.t.send("tulis " + "kata " * 30, wait=0.8)
        out = self.t.send("日本語", wait=0.5)
        self.assertNotIn("Traceback", out)


@unittest.skipUnless(pty and os.name == "posix", "butuh pty (POSIX)")
class AuthFlow(unittest.TestCase):
    def setUp(self):
        self.t = Pty()
        self.addCleanup(self.t.close)

    def test_banner_shows_before_login_prompt(self):
        full = self.t.plain()
        self.assertIn("Sign Up", full)
        self.assertIn("Log in", full)
        self.assertIn("CodinX", full)

    def test_signup_then_plan_choice_with_exact_english_prompt(self):
        self.t.send("1\r", 0.6)
        self.t.send("budi", 0.3)
        self.t.send("\r", 0.6)
        out = self.t.send("rahasia123\r", 1.0)
        self.assertIn("dibuat", out.lower())
        self.assertIn("There is Max, Pro and Free. Choose your method", out)
        out = self.t.send("2\r", 1.2)
        self.assertIn("Paket: PRO", out)

    def test_login_with_wrong_password_then_retry(self):
        self.t.send("1\r", 0.6)                                          # Sign Up
        self.t.send("sari\r", 0.6)
        self.t.send("benar123\r", 0.8)
        self.t.send("1\r", 1.0)                                          # pilihan paket (Max)
        self.t.send("/login\r", 0.8)                                     # paksa auth_flow lagi via perintah
        self.t.send("2\r", 0.6)                                          # Log in
        self.t.send("sari\r", 0.6)
        out = self.t.send("salah\r", 0.8)
        self.assertIn("salah", out.lower())
        self.t.send("y\r", 0.6)
        self.t.send("2\r", 0.6)                                          # diminta pilih lagi -> Log in
        self.t.send("sari\r", 0.5)
        out = self.t.send("benar123\r", 1.0)
        self.assertIn("kembali", out.lower())

    def test_login_persists_across_restarts_without_reprompting(self):
        self.t.send("1\r", 0.6)
        self.t.send("persisten\r", 0.6)
        self.t.send("pass1234\r", 0.8)
        out = self.t.send("3\r", 1.2)
        self.assertIn("masuk sebagai persisten", out)
        home = self.t.home
        self.t.close()
        self.t = Pty(env_extra={"HOME": home})
        self.assertNotIn("Sign Up", self.t.plain())
        self.assertIn("masuk sebagai persisten", self.t.plain())

    def test_admin_panel_via_bang_command_and_requires_login(self):
        self.t.send("1\r", 0.6)
        self.t.send("admintest\r", 0.6)
        self.t.send("pw12345\r", 0.8)
        self.t.send("1\r", 1.2)
        out = self.t.send("!admin_panel\r", 1.2)
        for needle in ("PANEL ADMIN", "Akun lokal", "Riwayat login", "admintest", "Perangkat"):
            self.assertIn(needle, out)
        self.assertNotIn("Traceback", out)

    def test_admin_panel_also_reachable_as_slash_command(self):
        self.t.send("1\r", 0.6)
        self.t.send("u2test\r", 0.6)
        self.t.send("pw12345\r", 0.8)
        self.t.send("1\r", 1.2)
        out = self.t.send("/admin_panel\r", 1.2)
        self.assertIn("PANEL ADMIN", out)

    def test_non_interactive_run_never_hits_the_login_prompt(self):
        """`run` (bukan REPL) tidak pernah menampilkan gerbang Sign Up/Log in, bahkan dengan stdin pipa terbuka."""
        from .helpers import run_cli_open_stdin
        srv, port = mock_proxy.start()
        try:
            env = {"CODINX_BASE_URL": f"http://127.0.0.1:{port}/v1", "CODINX_API_KEY": "k", "CODINX_MODEL": "m-full", "CODINX_AUTO_PROBE": "0"}
            out, finished = run_cli_open_stdin(self.t.home, self.t.cwd, ["run", "--no-color", "halo"], env, wait=10)
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertTrue(finished, "codinx run menggantung — kemungkinan auth_flow ikut terpanggil di jalur non-interaktif")
        self.assertNotIn("Sign Up", out)
        self.assertIn("CodinX", out)


if __name__ == "__main__":
    unittest.main()
