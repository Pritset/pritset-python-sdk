import asyncio
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import parse_qs, urlsplit

import httpx

from pritset import (
    AsyncPritsetClient,
    PritsetApiError,
    PritsetClient,
    PritsetTransportError,
    TemplateSort,
    Upload,
)


Request = Tuple[str, str, Dict[str, str], bytes]
REQUESTS: List[Request] = []


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._route()

    def do_POST(self) -> None:
        self._route()

    def do_PUT(self) -> None:
        self._route()

    def do_DELETE(self) -> None:
        self._route()

    def log_message(self, format: str, *args: object) -> None:
        return

    def _route(self) -> None:
        length = int(self.headers.get("content-length", "0"))
        body = self.rfile.read(length)
        headers = {key.lower(): value for key, value in self.headers.items()}
        REQUESTS.append((self.command, self.path, headers, body))
        parsed = urlsplit(self.path)
        query = parse_qs(parsed.query)

        if self.command == "GET" and parsed.path in ("/api/template", "/proxy/api/template"):
            if query.get("q") == ["validation-error"]:
                self._json(
                    400,
                    {
                        "title": "One or more validation errors occurred.",
                        "status": 400,
                        "errors": {"Name": ["The Name field is required."]},
                    },
                )
            elif query.get("q") == ["invalid-json"]:
                self._send(200, b"not-json", "application/json")
            else:
                self._json(
                    200,
                    {
                        "data": [
                            {
                                "id": "a1b2c3",
                                "name": "Monthly invoice",
                                "tags": "invoice,monthly",
                                "templateObject": None,
                            }
                        ],
                        "total": 1,
                    },
                )
            return
        if self.command == "POST" and parsed.path == "/api/template":
            self._json(
                200,
                {
                    "id": "created-template",
                    "name": "Monthly invoice",
                    "tags": "invoice,monthly",
                    "templateObject": None,
                },
            )
            return
        if self.command == "GET" and parsed.path == "/api/template/created-template":
            self._json(
                200,
                {
                    "template": {
                        "id": "created-template",
                        "name": "Monthly invoice",
                        "tags": "invoice,monthly",
                        "templateObject": None,
                    },
                    "fileInfo": {
                        "contentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "lastModified": "2026-07-15T09:30:00Z",
                        "objectName": "stored-template.docx",
                        "size": 9,
                    },
                },
            )
            return
        if self.command == "PUT" and parsed.path == "/api/template/created-template":
            self._json(
                200,
                {
                    "id": "created-template",
                    "name": "Monthly invoice 2026",
                    "tags": "invoice,2026",
                    "templateObject": None,
                },
            )
            return
        if self.command == "POST" and parsed.path == "/api/template/process/validate":
            self._json(200, True)
            return
        if self.command == "DELETE" and parsed.path == "/api/template/created-template":
            self._send(204, b"", None)
            return
        if self.command == "POST" and parsed.path == "/api/template/process/direct/template-1":
            self._send(200, b"%PDF-1.7 test", "application/pdf", {"X-Trace": '{"api.total":42}'})
            return
        if self.command == "GET" and parsed.path == "/api/template/download/template-1":
            self._send(
                200,
                b"fake-docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            return
        if self.command == "POST" and parsed.path == "/api/template/process/webhook/template-1":
            self._json(200, {"id": "57056f7462084dde8902421e9287ea2d"})
            return
        if self.command == "GET" and parsed.path == "/api/template/missing":
            self._send(404, b"Template not found", "text/plain", {"Retry-After": "3"})
            return
        if self.command == "GET" and parsed.path == "/api/template/huge-error":
            self._send(500, b"x" * (70 * 1024), "text/plain")
            return
        self._send(500, ("Unexpected route: %s %s" % (self.command, parsed.path)).encode(), "text/plain")

    def _json(self, status: int, value: object) -> None:
        self._send(status, json.dumps(value).encode(), "application/json")

    def _send(
        self,
        status: int,
        body: bytes,
        content_type: str,
        extra_headers: Dict[str, str] = None,
    ) -> None:
        self.send_response(status)
        if content_type:
            self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)


class ClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = "http://127.0.0.1:%d" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self) -> None:
        REQUESTS.clear()

    def client(self, base_url: str = None) -> PritsetClient:
        return PritsetClient(
            access_token="test-access-token",
            secret="test-secret",
            base_url=base_url or self.base_url,
            allow_insecure_http=True,
        )

    def test_requires_credentials_and_https_by_default(self) -> None:
        with self.assertRaisesRegex(ValueError, "access_token"):
            PritsetClient(access_token="", secret="secret")
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            PritsetClient(access_token="token", secret="secret", base_url="http://example.com")
        with self.assertRaisesRegex(ValueError, "credentials"):
            PritsetClient(
                access_token="token",
                secret="secret",
                base_url="https://user:password@example.com",
            )
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            PritsetClient(
                access_token="token",
                secret="secret",
                base_url="http://example.com",
                allow_insecure_http=True,
            )

    def test_repr_does_not_expose_credentials(self) -> None:
        value = self.client()
        try:
            rendered = repr(value) + repr(value._transport)
            self.assertNotIn("test-access-token", rendered)
            self.assertNotIn("test-secret", rendered)
        finally:
            value.close()

    def test_lists_templates_with_auth_headers_and_query_names(self) -> None:
        with self.client() as client:
            result = client.templates.list(
                search="invoice",
                page=2,
                page_size=20,
                sort=TemplateSort(sort_by="Name", sort_direction=1),
            )
        self.assertEqual(result.total, 1)
        self.assertEqual(result.data[0].name, "Monthly invoice")
        method, path, headers, _ = REQUESTS[0]
        self.assertEqual(method, "GET")
        self.assertEqual(headers["authorization"], "test-access-token")
        self.assertEqual(headers["x-secret"], "test-secret")
        self.assertIn("q=invoice", path)
        self.assertIn("p=2", path)
        self.assertIn("s=20", path)
        self.assertIn("sorts%5B0%5D.sortBy=Name", path)
        self.assertIn("sorts%5B0%5D.sortDirection=1", path)

    def test_preserves_base_url_path_prefix(self) -> None:
        with self.client(self.base_url + "/proxy") as client:
            self.assertEqual(client.templates.list().total, 1)
        self.assertEqual(urlsplit(REQUESTS[0][1]).path, "/proxy/api/template")

    def test_manages_templates_and_encodes_multipart_uploads(self) -> None:
        with self.client() as client:
            created = client.templates.create(
                name="Monthly invoice",
                tags="invoice,monthly",
                template=Upload(b"fake-docx", filename="invoice.docx"),
            )
            self.assertEqual(created.id, "created-template")
            headers = REQUESTS[0][2]
            body = REQUESTS[0][3]
            self.assertIn("multipart/form-data; boundary=", headers["content-type"])
            self.assertIn(b'name="name"', body)
            self.assertIn(b"Monthly invoice", body)
            self.assertIn(b'filename="invoice.docx"', body)

            details = client.templates.get("created-template")
            self.assertEqual(details.file_info.size, 9)
            updated = client.templates.update(
                "created-template", name="Monthly invoice 2026", tags="invoice,2026"
            )
            self.assertEqual(updated.name, "Monthly invoice 2026")
            self.assertIn("multipart/form-data; boundary=", REQUESTS[-1][2]["content-type"])

            valid = client.templates.validate(
                file=Upload(b"fake-docx", filename="invoice.docx"),
                data={"invoiceNumber": "INV-1024"},
            )
            self.assertTrue(valid)
            self.assertIn(b'name="file"', REQUESTS[-1][3])
            self.assertIn(b'name="data"', REQUESTS[-1][3])
            self.assertIn(b'{"invoiceNumber":"INV-1024"}', REQUESTS[-1][3])

            client.templates.delete("created-template")
            self.assertEqual(REQUESTS[-1][0], "DELETE")

    def test_streams_generated_pdfs_and_downloads(self) -> None:
        with self.client() as client:
            pdf = client.documents.generate("template-1", {"title": "Report"})
            self.assertEqual(pdf.content_type, "application/pdf")
            self.assertEqual(pdf.content_length, len(b"%PDF-1.7 test"))
            self.assertEqual(pdf.trace, '{"api.total":42}')
            self.assertEqual(pdf.to_bytes(), b"%PDF-1.7 test")

            with tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / "template.docx"
                client.templates.download("template-1").save_to_file(target)
                self.assertEqual(target.read_bytes(), b"fake-docx")

    def test_starts_webhook_generation_with_raw_json(self) -> None:
        with self.client() as client:
            job = client.documents.generate_webhook(
                "template-1",
                '{"title":"Raw JSON"}',
                "https://example.com/webhooks/pritset",
            )
            self.assertEqual(job.id, "57056f7462084dde8902421e9287ea2d")
            self.assertIn(b'{"title":"Raw JSON"}', REQUESTS[0][3])
            with self.assertRaisesRegex(ValueError, "credentials"):
                client.documents.generate_webhook(
                    "template-1", {}, "https://user:password@example.com/webhook"
                )

    def test_normalizes_api_errors(self) -> None:
        with self.client() as client:
            with self.assertRaises(PritsetApiError) as missing:
                client.templates.get("missing")
            self.assertEqual(missing.exception.status, 404)
            self.assertEqual(missing.exception.raw_body, "Template not found")
            self.assertEqual(missing.exception.retry_after, "3")

            with self.assertRaises(PritsetApiError) as invalid:
                client.templates.list(search="validation-error")
            self.assertEqual(invalid.exception.field_errors, {"Name": ["The Name field is required."]})
            self.assertIn("One or more validation errors occurred.", str(invalid.exception))

    def test_invalid_success_json_is_a_transport_error(self) -> None:
        with self.client() as client:
            with self.assertRaises(PritsetTransportError):
                client.templates.list(search="invalid-json")

    def test_caps_error_bodies_at_64_kib(self) -> None:
        with self.client() as client:
            with self.assertRaises(PritsetApiError) as error:
                client.templates.get("huge-error")
        self.assertEqual(len(error.exception.raw_body.encode("utf-8")), 64 * 1024)

    def test_transport_errors_drop_credential_bearing_context(self) -> None:
        class ExplodingTransport(httpx.BaseTransport):
            def handle_request(self, request: httpx.Request) -> httpx.Response:
                raise RuntimeError(
                    "leaked %s %s"
                    % (request.headers["authorization"], request.headers["x-secret"])
                )

        http_client = httpx.Client(transport=ExplodingTransport())
        client = PritsetClient(
            access_token="test-access-token",
            secret="test-secret",
            http_client=http_client,
        )
        try:
            with self.assertRaises(PritsetTransportError) as captured:
                client.templates.list()
            self.assertNotIn("test-access-token", str(captured.exception))
            self.assertNotIn("test-secret", str(captured.exception))
            self.assertIsNone(captured.exception.__cause__)
            self.assertIsNone(captured.exception.__context__)
        finally:
            client.close()
            self.assertFalse(http_client.is_closed)
            http_client.close()

    def test_redirects_are_not_followed(self) -> None:
        destination_requests = []

        class Destination(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                destination_requests.append(self.path)
                self.send_response(200)
                self.send_header("Content-Length", "21")
                self.end_headers()
                self.wfile.write(b'{"data":[],"total":0}')

            def log_message(self, format: str, *args: object) -> None:
                return

        destination = ThreadingHTTPServer(("127.0.0.1", 0), Destination)
        destination_thread = threading.Thread(target=destination.serve_forever, daemon=True)
        destination_thread.start()

        class Redirector(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self.send_response(302)
                self.send_header(
                    "Location",
                    "http://127.0.0.1:%d/stolen" % destination.server_address[1],
                )
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                return

        redirector = ThreadingHTTPServer(("127.0.0.1", 0), Redirector)
        redirector_thread = threading.Thread(target=redirector.serve_forever, daemon=True)
        redirector_thread.start()
        try:
            with self.client("http://127.0.0.1:%d" % redirector.server_address[1]) as client:
                with self.assertRaises(PritsetApiError) as error:
                    client.templates.list()
                self.assertEqual(error.exception.status, 302)
            self.assertEqual(destination_requests, [])
        finally:
            redirector.shutdown()
            redirector.server_close()
            destination.shutdown()
            destination.server_close()
            redirector_thread.join(timeout=5)
            destination_thread.join(timeout=5)

    def test_async_client_matches_sync_surface(self) -> None:
        async def run() -> None:
            async with AsyncPritsetClient(
                access_token="test-access-token",
                secret="test-secret",
                base_url=self.base_url,
                allow_insecure_http=True,
            ) as client:
                page = await client.templates.list()
                self.assertEqual(page.total, 1)
                created = await client.templates.create(
                    name="Monthly invoice",
                    tags="invoice,monthly",
                    template=Upload(b"fake-docx", filename="invoice.docx"),
                )
                self.assertEqual(created.id, "created-template")
                valid = await client.templates.validate(
                    file=Upload(b"fake-docx", filename="invoice.docx"),
                    data={"title": "Async validation"},
                )
                self.assertTrue(valid)
                pdf = await client.documents.generate("template-1", {"title": "Async"})
                self.assertEqual(await pdf.to_bytes(), b"%PDF-1.7 test")
                job = await client.documents.generate_webhook(
                    "template-1", {}, "https://example.com/webhook"
                )
                self.assertEqual(job.id, "57056f7462084dde8902421e9287ea2d")
                await client.templates.delete("created-template")

        asyncio.run(run())

    def test_async_requests_support_native_task_cancellation(self) -> None:
        async def run() -> None:
            started = asyncio.Event()
            never = asyncio.Event()

            async def slow_response(request: httpx.Request) -> httpx.Response:
                started.set()
                await never.wait()
                return httpx.Response(200, json={"data": [], "total": 0})

            http_client = httpx.AsyncClient(transport=httpx.MockTransport(slow_response))
            client = AsyncPritsetClient(
                access_token="test-access-token",
                secret="test-secret",
                http_client=http_client,
            )
            task = asyncio.create_task(client.templates.list())
            await started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            await client.close()
            self.assertFalse(http_client.is_closed)
            await http_client.aclose()

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
