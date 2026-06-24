# 12 — Repository Setup and Commands

## Existing repository

- GitHub: https://github.com/PhilFer1973/EInvoicing
- Local folder: `C:\Users\Philip\Downloads\EInvoicing`

## Recommended first steps

Open PowerShell:

```powershell
cd C:\Users\Philip\Downloads

# If repo is not cloned yet:
git clone https://github.com/PhilFer1973/EInvoicing EInvoicing

cd C:\Users\Philip\Downloads\EInvoicing
```

Copy this build pack into:

```text
C:\Users\Philip\Downloads\EInvoicing\docs
```

## Suggested repository initialization

```powershell
git status
git add docs
git commit -m "Add V1 e-invoicing build specification pack"
git push
```

## Frontend setup

```powershell
cd C:\Users\Philip\Downloads\EInvoicing
npm create vite@latest apps/web -- --template react-ts
cd apps/web
npm install
npm run dev
```

## Backend setup

```powershell
cd C:\Users\Philip\Downloads\EInvoicing
mkdir server
cd server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn pydantic openpyxl lxml sqlalchemy sqlmodel python-multipart qrcode pillow playwright pytest
python -m playwright install chromium
```

## Backend run command

```powershell
cd C:\Users\Philip\Downloads\EInvoicing\server
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

## Frontend environment

Create:

```text
apps/web/.env.local
```

With:

```text
VITE_API_BASE_URL=http://localhost:8000
```

## Backend health endpoint

Codex should create:

```text
GET http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

## Source materials

Recommended local source-material folders:

```text
docs/source_material/belgium_peppol/
docs/source_material/saudi_zatca/
```

Do not assume every source document should be committed to GitHub. If licensing or file size is uncertain, keep source materials locally and store only a manifest in Git.

## Git ignore additions

```gitignore
server/.venv/
server/storage/
server/*.db
apps/web/node_modules/
apps/web/dist/
docs/source_material/private/
```

## First Codex instruction

Use `docs/10_codex_build_prompt.md` and ask Codex to complete Milestone 1 only.
