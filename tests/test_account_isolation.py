import asyncio
import tempfile
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base
from app.main import app
from app.models.file import FileRecord
from app.routers.auth import get_db
from app.routers import files as files_router
from app.routers.files import detect_mime_type


class AccountIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.upload_dir = settings.UPLOAD_DIR
        cls.max_upload_size = settings.MAX_UPLOAD_SIZE_BYTES
        cls.storage_backend = settings.STORAGE_BACKEND
        settings.UPLOAD_DIR = Path(cls.temp_dir.name) / "uploads"
        settings.UPLOAD_DIR.mkdir()

        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=cls.engine)
        cls.session_factory = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        def override_get_db():
            db = cls.session_factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        cls.engine.dispose()
        settings.UPLOAD_DIR = cls.upload_dir
        settings.MAX_UPLOAD_SIZE_BYTES = cls.max_upload_size
        settings.STORAGE_BACKEND = cls.storage_backend
        cls.temp_dir.cleanup()

    def test_authentication_file_ownership_and_upload_limit(self):
        asyncio.run(self._exercise_account_access())

    def test_private_blob_round_trip_uses_account_scoped_path(self):
        asyncio.run(self._exercise_private_blob_storage())

    def test_mime_detection_uses_file_signature_before_extension(self):
        png_signature = b"\x89PNG\r\n\x1a\n" + bytes(16)
        self.assertEqual(detect_mime_type("misleading.txt", png_signature), "image/png")

    def test_homepage_precedes_sign_in(self):
        asyncio.run(self._check_homepage())

    async def _check_homepage(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn('id="landing-screen"', response.text)
        self.assertIn('id="landing-login"', response.text)
        self.assertIn('id="landing-register"', response.text)
        self.assertIn("Keep your files", response.text)
        self.assertIn('class="landing-visual"', response.text)
        self.assertEqual(response.text.count('class="landing-feature"'), 3)
        self.assertIn('<section id="auth-screen" class="auth-screen" hidden>', response.text)

    async def _exercise_account_access(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            anonymous_response = await client.get("/files/list")
            self.assertEqual(anonymous_response.status_code, 401)
            anonymous_upload = await client.post(
                "/files/upload",
                files={"file": ("anonymous.txt", b"private", "text/plain")},
            )
            self.assertEqual(anonymous_upload.status_code, 401)

            settings.MAX_UPLOAD_SIZE_BYTES = 4
            weak_password = await client.post(
                "/auth/register",
                json={"username": "student_weak", "password": "short"},
            )
            self.assertEqual(weak_password.status_code, 422)
            oversized_response = await client.post(
                "/auth/register",
                json={"username": "student_a", "password": "a-strong-password"},
            )
            self.assertEqual(oversized_response.status_code, 201)
            token_a = oversized_response.json()["access_token"]
            headers_a = {"Authorization": f"Bearer {token_a}"}
            too_large = await client.post(
                "/files/upload",
                headers=headers_a,
                files={"file": ("overflow.txt", b"12345", "text/plain")},
            )
            self.assertEqual(too_large.status_code, 413)
            self.assertEqual(list(settings.UPLOAD_DIR.rglob("*.upload")), [])

            settings.MAX_UPLOAD_SIZE_BYTES = self.max_upload_size
            register_b = await client.post(
                "/auth/register",
                json={"username": "student_b", "password": "another-strong-password"},
            )
            self.assertEqual(register_b.status_code, 201)
            headers_b = {"Authorization": f"Bearer {register_b.json()['access_token']}"}

            uploaded = await client.post(
                "/files/upload",
                headers=headers_a,
                files={"file": ("../../private.txt", b"private file contents", "text/plain")},
            )
            self.assertEqual(uploaded.status_code, 201)
            record = uploaded.json()
            self.assertEqual(record["filename"], "private.txt")
            self.assertEqual(
                record["sha256"],
                "b93291725c16d1d4d144d81d7f27bce53b6515433a236f40115d9dda48487a4f",
            )

            list_a = await client.get("/files/list", headers=headers_a)
            list_b = await client.get("/files/list", headers=headers_b)
            self.assertEqual([item["id"] for item in list_a.json()], [record["id"]])
            self.assertEqual(list_b.json(), [])

            foreign_download = await client.get(
                f"/files/download/{record['id']}",
                headers=headers_b,
            )
            foreign_delete = await client.delete(
                f"/files/delete/{record['id']}",
                headers=headers_b,
            )
            self.assertEqual(foreign_download.status_code, 404)
            self.assertEqual(foreign_delete.status_code, 404)

            own_download = await client.get(
                f"/files/download/{record['id']}",
                headers=headers_a,
            )
            self.assertEqual(own_download.status_code, 200)
            self.assertEqual(own_download.content, b"private file contents")

            own_delete = await client.delete(
                f"/files/delete/{record['id']}",
                headers=headers_a,
            )
            self.assertEqual(own_delete.status_code, 200)
            self.assertEqual((await client.get("/files/list", headers=headers_a)).json(), [])

    async def _exercise_private_blob_storage(self):
        settings.STORAGE_BACKEND = "vercel_blob"
        stored_blobs = {}

        async def fake_put(pathname, body, *, access, content_type):
            self.assertEqual(access, "private")
            stored_blobs[pathname] = bytes(body)
            return SimpleNamespace(pathname=pathname)

        @asynccontextmanager
        async def fake_stream(pathname, *, access):
            self.assertEqual(access, "private")

            class Download:
                metadata = SimpleNamespace(content_type="text/plain")

                def __aiter__(self):
                    async def chunks():
                        yield stored_blobs[pathname]

                    return chunks()

            yield Download()

        async def fake_delete(pathname):
            stored_blobs.pop(pathname, None)

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            registered = await client.post(
                "/auth/register",
                json={"username": "blob_student", "password": "a-strong-blob-password"},
            )
            self.assertEqual(registered.status_code, 201)
            headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}

            with (
                patch.object(files_router.blob, "put_blob", side_effect=fake_put),
                patch.object(files_router.blob, "stream_blob", side_effect=fake_stream),
                patch.object(files_router.blob, "delete_blob", side_effect=fake_delete),
            ):
                uploaded = await client.post(
                    "/files/upload",
                    headers=headers,
                    files={"file": ("notes.txt", b"private blob contents", "text/plain")},
                )
                self.assertEqual(uploaded.status_code, 201)
                record = uploaded.json()
                db = self.session_factory()
                database_record = db.query(FileRecord).filter_by(id=record["id"]).one()
                self.assertTrue(database_record.stored_path.startswith("users/"))
                self.assertTrue(database_record.stored_path.endswith(".upload"))
                db.close()

                downloaded = await client.get(
                    f"/files/download/{record['id']}",
                    headers=headers,
                )
                self.assertEqual(downloaded.status_code, 200)
                self.assertEqual(downloaded.content, b"private blob contents")
                self.assertEqual(downloaded.headers["cache-control"], "private, no-store")

                deleted = await client.delete(
                    f"/files/delete/{record['id']}",
                    headers=headers,
                )
                self.assertEqual(deleted.status_code, 200)
                self.assertEqual(stored_blobs, {})


if __name__ == "__main__":
    unittest.main()
