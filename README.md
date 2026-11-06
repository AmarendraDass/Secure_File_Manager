# Secure File Manager

A browser-based file workspace for learning about file metadata and integrity. Users create an account, upload files, review MIME-type and extension information, and record SHA-256 checksums. File-list, download, and delete operations require a signed-in account and are restricted to that account's records.

## Important security limits

- Accounts isolate file records, but uploaded files are **not encrypted at rest**. Do not upload sensitive or regulated data.
- SHA-256 helps detect changes; it is not encryption, malware scanning, or proof of a file's safety.
- Registration is open and does not include email verification or password recovery.
- The app enforces a 4 MiB upload limit by default so an upload can fit within Vercel Functions' request-body limit. Raise it only when using a host with a higher request limit.
- Put a public deployment behind HTTPS, configure host restrictions and a reverse-proxy request-body limit, use encrypted persistent storage, and add platform-level rate limiting for account endpoints before inviting users.

## Local development (Windows PowerShell)

Use Python 3.12. If an old virtual environment refers to a Python installation that has been removed, create a new environment rather than trying to repair that one in place:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Replace `SECRET_KEY` in `.env` with a unique random value of at least 32 characters. To generate one and set it for the current PowerShell session:

```powershell
$env:SECRET_KEY = (python -c "import secrets; print(secrets.token_urlsafe(48))")
```

Start the app:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Open [http://127.0.0.1:8001](http://127.0.0.1:8001), create an account, and sign in. The API docs are available at `/docs` in development only.

Run the account-isolation and upload-limit tests with:

```powershell
python -m unittest discover -s tests -v
```

Environment variables:

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Signs access tokens; set a unique secret before deployment | Development-only value |
| `ENVIRONMENT` | Set to `production` to enable production checks and headers | `development` |
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///./app.db` |
| `UPLOAD_DIR` | Private file storage root | `app/uploads` |
| `STORAGE_BACKEND` | `local` for development or `vercel_blob` for Vercel | `local` |
| `MAX_UPLOAD_SIZE_BYTES` | Maximum accepted upload size | `4194304` |
| `ALLOWED_HOSTS` | Comma-separated trusted hostnames | Unrestricted for local development |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins, if a separate frontend needs them | Same-origin only |

When `libmagic` is available, the app detects MIME types from file contents. Otherwise it uses the bundled `filetype` signature detector and only falls back to the extension mapping for formats it cannot identify. Extension matching is a warning, not a malware scan or full content validation.

## Deploy to Vercel

The root `main.py` exports the FastAPI app for Vercel's Python runtime. Vercel Functions are temporary, so Vercel deployments require PostgreSQL and a **private** Vercel Blob store; the local SQLite/file-storage backend is rejected at startup on Vercel.

1. Push this project to a GitHub repository and import it from the Vercel dashboard. Keep the project root as the Root Directory. Vercel detects the root `main.py`, `requirements.txt`, and `.python-version` (Python 3.12).
2. In Vercel Storage, create a **private** Blob store and connect it to this project. The Python SDK uses Vercel's project OIDC credentials when connected.
3. Connect a hosted PostgreSQL database (for example through the Vercel Marketplace) and copy its TLS-enabled connection string into the Vercel environment variable `DATABASE_URL`.
4. Add these environment variables for the Production environment:

   | Name | Value |
   |---|---|
   | `ENVIRONMENT` | `production` |
   | `STORAGE_BACKEND` | `vercel_blob` |
   | `DATABASE_URL` | Hosted PostgreSQL connection string |
   | `SECRET_KEY` | Unique random value with at least 32 characters |
   | `MAX_UPLOAD_SIZE_BYTES` | `4194304` |
   | `ALLOWED_HOSTS` | Your exact `your-project.vercel.app` hostname and any custom domain, comma-separated |

   Vercel provides `VERCEL` and the current `VERCEL_URL`. The app uses that deployment hostname for host validation; add custom domains to `ALLOWED_HOSTS`. Do not use `*`.
5. Deploy from the Vercel dashboard. Open the resulting HTTPS URL, create an account, and test with two accounts to confirm each sees only its own files. The app creates its database tables on first start.

Use separate database and Blob resources for Preview deployments if you enable previews; do not let preview builds access production user files. Existing local SQLite data and uploaded files are not copied to the hosted services. The Vercel request-body limit is about 4.5 MB for the whole multipart request, so the configured file limit is 4 MiB.

This makes access account-private but does not add application-managed encryption at rest, malware scanning, email verification, password recovery, or rate limiting. Treat this as a student project, not a service for sensitive or regulated files. Confirm the storage providers' encryption, retention, access, and backup terms before uploading anything confidential.

## Existing local databases

On startup, the app adds an `owner_id` column to an older `files` table if needed. Legacy file records are left unassigned and are not visible to any account. Back up the database before upgrading; do not make those records public to work around the migration.

## Main features

- Browser-based account registration and sign-in
- Account-scoped upload, listing, download, and deletion
- One-hour signed access tokens, cleared when signing out
- File size enforcement and generated storage names
- MIME metadata and extension-mismatch warning
- SHA-256 checksum calculation
- Responsive dashboard with vault search and integrity summary
- Security response headers and a health endpoint at `/health`
