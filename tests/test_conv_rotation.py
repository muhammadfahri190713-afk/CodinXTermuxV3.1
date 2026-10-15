"""Rotasi id percakapan (diam-diam): saat endpoint gagal di tengah giliran (umum setelah banyak tool call) atau
setelah N tool call, CodinX mengganti id yang dikirim ke API lalu mengulang -- TANPA mengubah sesi/riwayat/memori
yang terlihat user, dan TANPA mencetak apa pun ke terminal kecuali percobaan ulang itu juga gagal."""
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from cx import agent, app as app_mod, config
from cx.session import Session


class ScriptedProxy:
    """Proxy tiruan yang perilakunya diprogram per-request: daftar aksi dijalankan berurutan.

    Aksi: ("text", s) balas teks biasa | ("tool", nama, args) minta panggil tool |
          ("fail", kode) balas HTTP error | sisanya (bila aksi habis) balas teks "selesai akhir"."""

    def __init__(self, script):
        self.script = list(script)
        self.requests = []          # [{"conv": str, "n_msgs": int}]
        self.i = 0
        handler = self._make_handler()
        self.srv = HTTPServer(("127.0.0.1", 0), handler)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def _make_handler(self):
        proxy = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                self._json({"data": [{"id": "m-test"}]})

            def _json(self, obj, code=200):
                b = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                proxy.requests.append({"conv": self.headers.get("X-Conversation-Id"), "n_msgs": len(body["messages"])})
                approx_tokens = max(50, sum(len(str(m.get("content") or "")) for m in body["messages"]) // 3)
                action = proxy.script[proxy.i] if proxy.i < len(proxy.script) else ("text", "selesai akhir")
                proxy.i += 1
                if action[0] == "fail":
                    return self._json({"error": {"message": "context length / conversation too long"}}, action[1])
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                if action[0] == "tool":
                    _, name, args = action
                    s = json.dumps(args)
                    self.wfile.write(("data: " + json.dumps({"choices": [{"delta": {"tool_calls": [
                        {"index": 0, "id": "c1", "function": {"name": name, "arguments": s}}]}}]}) + "\n\n").encode())
                else:
                    text = action[1]
                    self.wfile.write(("data: " + json.dumps({"choices": [{"delta": {"content": text}}]}) + "\n\n").encode())
                self.wfile.write(("data: " + json.dumps({"choices": [], "usage": {"prompt_tokens": approx_tokens, "completion_tokens": 5, "total_tokens": approx_tokens + 5}}) + "\n\n").encode())
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
        return H

    def stop(self):
        self.srv.shutdown()
        self.srv.server_close()


class RotationCase(unittest.TestCase):
    def make_app(self, script, cfg_extra=None):
        self.proxy = ScriptedProxy(script)
        self.addCleanup(self.proxy.stop)
        cwd = tempfile.mkdtemp()
        cfg = config.load(cwd)
        cfg.update(base_url=f"http://127.0.0.1:{self.proxy.port}/v1", model="m-test", tool_mode="native", history_mode="native",
                  auto_probe=False, tier="max", trial_mode=True)
        cfg.update(cfg_extra or {})
        a = app_mod.App(cfg)
        a.key = "k"
        a.ui.quiet = True
        a.perms.auto = True
        self.calls = {"info": [], "warn": [], "err": [], "ok": []}
        for kind in self.calls:
            setattr(a.ui, kind, (lambda k: lambda msg: self.calls[k].append(msg))(kind))
        return a

    def headers_seen(self):
        return [r["conv"] for r in self.proxy.requests]


class Reactive(RotationCase):
    def test_mid_turn_failure_is_silently_retried_with_a_new_conv_id_and_nothing_is_printed(self):
        a = self.make_app([
            ("tool", "read", {"path": "x.txt"}),     # step 0: model minta tool
            ("fail", 403),                            # step 1 percobaan 1: proxy "memotong"
            ("text", "Selesai setelah rotasi!"),       # step 1 percobaan 2 (id baru): berhasil
        ])
        sid_before = a.session.id
        msgs_before = len(a.session.messages)
        final = a.agent.turn("tolong baca file")
        self.assertEqual(final, "Selesai setelah rotasi!")
        self.assertEqual(a.session.id, sid_before)                        # sesi TIDAK berubah
        self.assertGreater(len(a.session.messages), msgs_before)          # riwayat bertambah normal (tidak direset)
        headers = self.headers_seen()
        self.assertEqual(len(headers), 3)
        self.assertEqual(headers[0], headers[1])                          # step0 & percobaan gagal pakai id yang sama
        self.assertNotEqual(headers[1], headers[2])                       # percobaan ulang pakai id BARU
        for kind, msgs in self.calls.items():                             # SAMA SEKALI tidak ada output apa pun
            self.assertEqual(msgs, [], f"ui.{kind} terpanggil: {msgs}")

    def test_first_message_failure_is_still_reported_normally(self):
        a = self.make_app([("fail", 403)])
        final = a.agent.turn("halo")
        self.assertEqual(final, "")
        self.assertTrue(self.calls["err"], "kegagalan di pesan PERTAMA (bukan di tengah tool) harus tetap dilaporkan")

    def test_if_the_retry_also_fails_the_error_surfaces(self):
        a = self.make_app([
            ("tool", "read", {"path": "x.txt"}),
            ("fail", 403),
            ("fail", 403),                             # percobaan ulang pun tetap gagal -> harus terlihat
        ])
        a.agent.turn("baca file")
        self.assertTrue(self.calls["err"], "kegagalan yang menetap harus tetap dilaporkan ke user")

    def test_rotation_is_inert_when_conv_source_is_server(self):
        a = self.make_app([
            ("tool", "read", {"path": "x.txt"}),
            ("fail", 403),
            ("text", "ok"),
        ], cfg_extra={"conv_source": "server", "conv_field": "conversation_id"})
        a.agent.turn("baca file")
        self.assertTrue(all(h is None for h in self.headers_seen()))


class Proactive(RotationCase):
    def test_rotates_silently_every_N_tool_calls_within_one_turn(self):
        n = agent.Agent.TOOLS_PER_ROTATE
        script = [("tool", "read", {"path": f"f{i}.txt"}) for i in range(n + 3)] + [("text", "selesai")]
        a = self.make_app(script)
        sid_before = a.session.id
        final = a.agent.turn("baca banyak file")
        self.assertEqual(final, "selesai")
        self.assertEqual(a.session.id, sid_before)
        headers = self.headers_seen()
        self.assertGreater(len(set(headers)), 1, "harus ada setidaknya satu rotasi id selama giliran panjang ini")
        for kind, msgs in self.calls.items():
            self.assertEqual(msgs, [], f"ui.{kind} terpanggil saat rotasi proaktif: {msgs}")

    def test_short_turns_never_rotate(self):
        a = self.make_app([("tool", "read", {"path": "a.txt"}), ("text", "selesai")])
        a.agent.turn("satu file saja")
        self.assertEqual(len(set(self.headers_seen())), 1)


class SessionUnaffected(RotationCase):
    def test_conv_token_is_not_persisted_to_the_session_file(self):
        a = self.make_app([("tool", "read", {"path": "x.txt"}), ("fail", 403), ("text", "ok")])
        a.agent.turn("baca")
        with open(a.session.path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertNotIn("conv_token", data)
        self.assertEqual(data["id"], a.session.id)

    def test_fresh_session_gets_a_fresh_token_equal_to_its_id(self):
        s = Session("/tmp")
        self.assertEqual(s.conv_token, s.id)
        s.rotate_conv_token()
        self.assertNotEqual(s.conv_token, s.id)


if __name__ == "__main__":
    unittest.main()
