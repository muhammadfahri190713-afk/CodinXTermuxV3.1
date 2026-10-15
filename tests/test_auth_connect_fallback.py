import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

from cx import adminpanel, auth, config, connectors, fallback
from cx.session import Session


class AuthCase(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        p = mock.patch.object(auth, "FILE", os.path.join(self.d, "auth.json"))
        p.start()
        self.addCleanup(p.stop)
        g = mock.patch("cx.geo.lookup", return_value={"ip": "203.0.113.5", "city": "Kota", "province": "Prov", "country": "ID"})
        g.start()
        self.addCleanup(g.stop)


class SignupLogin(AuthCase):
    def test_signup_persists_and_hashes_password_not_plaintext(self):
        ok, msg = auth.signup("budi", "rahasia123")
        self.assertTrue(ok, msg)
        self.assertEqual(auth.current_user(), "budi")
        with open(auth.FILE) as f:
            raw = f.read()
        self.assertNotIn("rahasia123", raw)
        self.assertEqual(os.stat(auth.FILE).st_mode & 0o777, 0o600)

    def test_duplicate_username_rejected_case_insensitively(self):
        auth.signup("Budi", "pass1234")
        ok, msg = auth.signup("budi", "lain1234")
        self.assertFalse(ok)
        self.assertIn("terdaftar", msg)

    def test_username_and_password_validation(self):
        self.assertFalse(auth.signup("ab", "pass1234")[0])         # terlalu pendek
        self.assertFalse(auth.signup("valid_name", "123")[0])      # password terlalu pendek
        self.assertTrue(auth.signup("valid_name", "1234")[0])

    def test_login_correct_and_wrong_password(self):
        auth.signup("sari", "benar123")
        auth.logout()
        ok, msg = auth.login("sari", "salah")
        self.assertFalse(ok)
        self.assertIsNone(auth.current_user())
        ok, msg = auth.login("sari", "benar123")
        self.assertTrue(ok)
        self.assertEqual(auth.current_user(), "sari")

    def test_login_count_and_last_login_update(self):
        auth.signup("u1test", "pass1234")
        auth.logout()
        auth.login("u1test", "pass1234")
        auth.login("u1test", "pass1234")
        d = auth.admin_data()
        u = d["users"][0]
        self.assertEqual(u["login_count"], 3)                      # signup = 1 login + 2 login eksplisit

    def test_logout_clears_current_but_keeps_account(self):
        auth.signup("xtest", "pass1234")
        who = auth.logout()
        self.assertEqual(who, "xtest")
        self.assertIsNone(auth.current_user())
        self.assertTrue(auth.has_any_account())

    def test_events_capture_ip_and_location_and_cap_length(self):
        auth.signup("rec", "pass1234")
        d = auth.admin_data()
        ev = d["events"][-1]
        self.assertEqual((ev["ip"], ev["location"]), ("203.0.113.5", "Kota, Prov, ID"))
        for _ in range(auth.MAX_EVENTS + 20):
            auth.login("rec", "salah")
        self.assertLessEqual(len(auth.load()["events"]), auth.MAX_EVENTS)

    def test_no_account_state(self):
        self.assertFalse(auth.has_any_account())
        self.assertIsNone(auth.current_user())
        self.assertEqual(auth.admin_data()["users"], [])


class AdminPanelData(AuthCase):
    def test_build_sections_reflect_auth_state(self):
        auth.signup("panelis", "pass1234")
        cfg = {"model": "m-1", "base_url": "https://x.test/v1", "theme": "auto", "design": {}, "tier": "free", "trial_mode": True}
        cwd = tempfile.mkdtemp()
        with mock.patch.object(config, "KEYFILE", os.path.join(self.d, "k.enc")), mock.patch.object(config, "env", return_value=""):
            sections = adminpanel.build(cfg, Session(cwd), cwd)
        titles = [t for t, _, _ in sections]
        self.assertIn("Akun lokal perangkat ini", titles)
        acc_rows = dict(zip(titles, [r for _, _, r in sections]))["Akun lokal perangkat ini"]
        self.assertEqual(acc_rows[0][0], "panelis")
        dev_rows = {r[0]: r[1] for r in dict(zip(titles, [r for _, _, r in sections]))["Perangkat & jaringan"]}
        self.assertEqual(dev_rows["IP publik"], "203.0.113.5")

    def test_config_section_never_leaks_raw_key(self):
        auth.signup("x", "pass1234")
        cfg = {"model": "m-1", "base_url": "https://x.test/v1", "theme": "auto", "design": {}, "tier": "free", "trial_mode": True}
        with mock.patch.object(config, "env", return_value=""), mock.patch.object(config, "get_key", return_value="sk-RAHASIASEKALI12345"):
            sections = adminpanel.build(cfg, Session(tempfile.mkdtemp()), tempfile.mkdtemp())
        flat = str(sections)
        self.assertNotIn("sk-RAHASIASEKALI12345", flat)


class _ModelsHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        auth_hdr = self.headers.get("Authorization", "")
        xkey = self.headers.get("x-api-key", "")
        ver = self.headers.get("anthropic-version", "")
        if self.path.startswith("/v1/models") and xkey and ver:
            body = json.dumps({"data": [{"id": "claude-opus-4-7"}, {"id": "claude-sonnet-4-5"}]}).encode()
        elif self.path.endswith("/models") and auth_hdr == "Bearer k":
            body = json.dumps({"data": [{"id": "model-a"}, {"id": "model-b"}]}).encode()
        else:
            self.send_response(401)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class Connectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), _ModelsHandler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def test_openai_style_listing(self):
        ids, style = connectors.list_models(f"http://127.0.0.1:{self.port}/v1", "k")
        self.assertEqual((sorted(ids), style), (["model-a", "model-b"], "openai"))

    def test_anthropic_style_listing_falls_back_from_openai(self):
        ids, style = connectors.list_models(f"http://127.0.0.1:{self.port}", "k", style="anthropic")
        self.assertEqual((sorted(ids), style), (["claude-opus-4-7", "claude-sonnet-4-5"], "anthropic"))

    def test_style_detection_by_domain(self):
        self.assertEqual(connectors.style_for("https://api.anthropic.com"), "anthropic")
        self.assertEqual(connectors.style_for("https://openrouter.ai/api/v1"), "openai")
        self.assertEqual(connectors.style_for("https://inttelix.vercel.app/api/v1"), "openai")
        self.assertEqual(connectors.style_for("https://random-proxy.example/v1"), "openai")
        self.assertEqual(connectors.label_for("https://openrouter.ai/api/v1"), "OpenRouter")

    def test_all_profiles_fail_raises_connect_error_with_attempts(self):
        with self.assertRaises(connectors.ConnectError) as cm:
            connectors.list_models("http://127.0.0.1:1", "k", timeout=1)
        self.assertGreaterEqual(len(cm.exception.attempts), 1)

    def test_wrong_credentials_tries_other_style_before_failing(self):
        with self.assertRaises(connectors.ConnectError) as cm:
            connectors.list_models(f"http://127.0.0.1:{self.port}/v1", "", style="openai", timeout=3)
        self.assertEqual(len(cm.exception.attempts), 2)              # openai lalu anthropic, keduanya ditolak tanpa key


class FallbackAssistant(unittest.TestCase):
    def test_unavailable_without_both_env_vars(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            config._dotenv = None
            for k in ("CODINX_FALLBACK_BASE_URL", "CODINX_FALLBACK_API_KEY", "CODINX_FALLBACK_MODEL"):
                os.environ.pop(k, None)
            self.assertFalse(fallback.available())
            self.assertIsNone(fallback.active_config())

    def test_available_and_used_when_both_set(self):
        env = {"CODINX_FALLBACK_BASE_URL": "https://fb.test/api", "CODINX_FALLBACK_API_KEY": "sk-fb-key", "CODINX_FALLBACK_MODEL": "claude-opus-4-7"}
        with mock.patch.dict(os.environ, env):
            config._dotenv = None
            self.assertTrue(fallback.available())
            cfg = fallback.active_config()
            self.assertEqual((cfg["model"], cfg["base_url"].endswith("/v1")), ("claude-opus-4-7", True))
            self.assertNotIn("sk-fb-key", str({k: v for k, v in cfg.items() if k != "_key"}))

    def test_no_real_secret_is_hardcoded_anywhere_in_shipped_source(self):
        """Regresi penting: pastikan tidak ada kunci sungguhan yang ikut ter-commit ke kode."""
        import cx.fallback as mod
        with open(mod.__file__, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("sk-RopsTwDgjHpUA8UNKxz6np", src)
        self.assertNotIn("api.manus.im", src)

    def test_ask_uses_the_fallback_endpoint_not_tools(self):
        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                assert body.get("tools") is None
                b = json.dumps({"choices": [{"message": {"content": "Halo, saya GPT 5.6 Sol."}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)
        srv = HTTPServer(("127.0.0.1", 0), H)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            env = {"CODINX_FALLBACK_BASE_URL": f"http://127.0.0.1:{port}/v1", "CODINX_FALLBACK_API_KEY": "k", "CODINX_FALLBACK_MODEL": "claude-opus-4-7"}
            with mock.patch.dict(os.environ, env):
                config._dotenv = None
                self.assertIn("GPT 5.6 Sol", fallback.ask("halo"))
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
