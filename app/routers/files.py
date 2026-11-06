from contextlib import AsyncExitStack
import hashlib
import logging
import mimetypes
import os
import uuid
from pathlib import Path
from urllib.parse import quote

import aiofiles
import filetype
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from starlette.background import BackgroundTask
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from vercel import blob

try:
    import magic
except ImportError:  # Windows may not have libmagic installed.
    magic = None

from app.core.config import settings
from app.models.file import FileRecord
from app.models.user import User
from app.routers.auth import get_current_user, get_db

router = APIRouter()
logger = logging.getLogger(__name__)


def safe_display_name(filename: str | None) -> str:
    name = (filename or "unnamed-file").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(character for character in name if character.isprintable()).strip(" .")
    return (name or "unnamed-file")[:255]


def detect_mime_type(filename: str, sample: bytes, stored_path: Path | None = None) -> str:
    if magic is not None:
        if stored_path is not None:
            return magic.from_file(str(stored_path), mime=True)
        if sample:
            return magic.from_buffer(sample, mime=True)

    detected_type = filetype.guess(sample)
    if detected_type is not None:
        return detected_type.mime
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filename = safe_display_name(file.filename)
    extension = filename.rpartition(".")[2].lower() if "." in filename else ""
    use_blob = settings.STORAGE_BACKEND == "vercel_blob"
    owner_directory = settings.UPLOAD_DIR / str(current_user.id)
    if not use_blob:
        owner_directory.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            owner_directory.chmod(0o700)
    stored_path = owner_directory / f"{uuid.uuid4().hex}.upload"
    blob_pathname = None
    checksum = hashlib.sha256()
    size = 0

    try:
        if file.size is not None and file.size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_BYTES}-byte upload limit",
            )
        if use_blob:
            content = bytearray()
            sample = bytearray()
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_BYTES}-byte upload limit",
                    )
                checksum.update(chunk)
                content.extend(chunk)
                if len(sample) < 8192:
                    sample.extend(chunk[: 8192 - len(sample)])

            mime_type = detect_mime_type(filename, bytes(sample))

            blob_path = f"users/{current_user.id}/{uuid.uuid4().hex}.upload"
            uploaded = await blob.put_blob(
                blob_path,
                content,
                access="private",
                content_type=mime_type,
            )
            blob_pathname = uploaded.pathname
            stored_value = blob_pathname
        else:
            sample = bytearray()
            async with aiofiles.open(stored_path, "xb") as destination:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > settings.MAX_UPLOAD_SIZE_BYTES:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_BYTES}-byte upload limit",
                        )
                    checksum.update(chunk)
                    if len(sample) < 8192:
                        sample.extend(chunk[: 8192 - len(sample)])
                    await destination.write(chunk)
            if os.name == "posix":
                stored_path.chmod(0o600)

            mime_type = detect_mime_type(filename, bytes(sample), stored_path)
            stored_value = str(stored_path)

        expected_mime, _ = mimetypes.guess_type(filename)
        extension_mismatch = expected_mime is None or expected_mime != mime_type

        record = FileRecord(
            owner_id=current_user.id,
            filename=filename,
            stored_path=stored_value,
            mime_type=mime_type,
            sha256=checksum.hexdigest(),
            extension=extension,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
    except BaseException:
        db.rollback()
        if not use_blob:
            stored_path.unlink(missing_ok=True)
        if blob_pathname is not None:
            try:
                await blob.delete_blob(blob_pathname)
            except Exception:
                logger.exception("Could not remove an unrecorded private blob %s", blob_pathname)
        raise
    finally:
        await file.close()

    return {
        "id": record.id,
        "filename": record.filename,
        "mime_type": record.mime_type,
        "sha256": record.sha256,
        "extension": record.extension,
        "extension_mismatch": extension_mismatch,
    }


@router.get("/list")
def list_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    records = (
        db.query(FileRecord)
        .filter(FileRecord.owner_id == current_user.id)
        .order_by(FileRecord.upload_time.desc(), FileRecord.id.desc())
        .all()
    )
    return [
        {
            "id": record.id,
            "filename": record.filename,
            "mime_type": record.mime_type,
            "sha256": record.sha256,
            "extension": record.extension,
            "upload_time": record.upload_time,
        }
        for record in records
    ]


@router.get("/download/{file_id}")
async def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = (
        db.query(FileRecord)
        .filter(FileRecord.id == file_id, FileRecord.owner_id == current_user.id)
        .first()
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    if settings.STORAGE_BACKEND == "vercel_blob":
        stack = AsyncExitStack()
        try:
            download = await stack.enter_async_context(
                blob.stream_blob(record.stored_path, access="private")
            )
        except blob.BlobError as error:
            await stack.aclose()
            if isinstance(error, blob.BlobNotFoundError):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found",
                ) from None
            raise

        return StreamingResponse(
            download,
            media_type=record.mime_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(record.filename, safe='')}",
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "private, no-store",
            },
            background=BackgroundTask(stack.aclose),
        )

    if not Path(record.stored_path).is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileResponse(
        path=record.stored_path,
        filename=record.filename,
        media_type=record.mime_type,
    )


@router.delete("/delete/{file_id}")
async def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = (
        db.query(FileRecord)
        .filter(FileRecord.id == file_id, FileRecord.owner_id == current_user.id)
        .first()
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if settings.STORAGE_BACKEND == "vercel_blob":
        await blob.delete_blob(record.stored_path)
    else:
        Path(record.stored_path).unlink(missing_ok=True)
    db.delete(record)
    db.commit()
    return {"msg": "File deleted"}
