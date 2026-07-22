# Copilot Instructions

Real-time doctor↔patient voice translation web app. Browser mic audio streams over
WebSocket to a FastAPI backend, which relays to the **Soniox** STT API and returns
transcription + two-way translation. Post-conversation LLM steps (summary, translation,
PDF) run through **LangChain + OpenAI-compatible** endpoints.

> Note: the actual layout differs from the "Project Structure" section of the root
> `README.md`. Trust the code paths below over the README when they conflict.

## Layout

All application code lives under `doctor_patient_app/` (the repo root only holds the
README and this app folder).

- `backend/` — FastAPI app. Entry point `main.py` (run from **inside** `backend/`).
  - `main.py` — HTTP + `/ws` WebSocket endpoints, LLM summary/translate/PDF endpoints.
  - `soniox_ws.py` — `SonioxWSClient`, wraps the Soniox realtime WS (`wss://stt-rt.soniox.com`).
  - `langchain_router.py` — `LangChainRouter`, normalizes Soniox tokens and routes them
    into the three display "boxes" (original / doctor / patient). No LLM calls here.
  - `models.py` — Pydantic models + `BoxBuffers`; Indic-script helpers (`is_indic_char`,
    `smart_join`) for safe token joining.
  - `database.py` — `Database` / `DoctorPatientDB`, `get_db()`. Reads existing PostgreSQL
    `pces_users` (doctors) and `patient` tables; does **not** create tables.
  - `azure_storage.py` — `AzureStorageManager`, uploads generated PDFs to Azure Blob.
  - `utils.py` — `RecordingManager`, writes conversation JSON to `backend/recordings/`.
  - `audio_stream.py` — `AudioStreamProcessor`, PCM16 buffering (16 kHz mono, 1600-sample chunks).
- `frontend/` — static assets served by FastAPI: `index.html`, `medical_summary.html`,
  `app.js`, `styles.css` (no build step; plain JS).
- `init_database.py` — connectivity check only (verifies `pces_users`/`patient` exist).

## Run / build / test

No test suite, linter, or build tooling exists. To run:

```bash
cd doctor_patient_app
./start.sh                       # creates venv (python3.12), installs deps, runs backend
```

Manual equivalent (note: server must start from within `backend/`, since paths and
`recordings/` are resolved relative to that cwd):

```bash
cd doctor_patient_app && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt   # start.sh actually uses `uv pip install`
cd backend && python main.py      # serves http://localhost:8000
```

`uvicorn backend.main:app` from the app root also works, but running `python main.py`
from `backend/` is the primary path.

## Configuration

All secrets/config come from `doctor_patient_app/.env` (git-ignored). Required keys:
`SONIOX_API_KEY`, `SONIOX_MODEL`, `OPENAI_API_KEY`, `base_url`, `llm_model_name`,
Postgres (`DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD`), and optional
`AZURE_STORAGE_CONNECTION_STRING` / `AZURE_STORAGE_CONTAINER_NAME`. Never commit `.env`
or hardcode these values.

## Conventions & architecture notes

- **Two async pumps per WebSocket session** (`main.py` `/ws`): `receive_from_browser`
  forwards audio to Soniox; `receive_from_soniox` feeds tokens through `LangChainRouter`
  and pushes `{type, tokens, boxes}` back to the browser. First browser message is a JSON
  config (`doctor_lang`, `patient_lang`, `doctor_name`, `patient_id`, `patient_name`);
  subsequent messages are binary PCM16.
- **Three-box model** is central: every token is categorized into `original`,
  `doctor`, or `patient`. When `doctor_lang == patient_lang`, `LangChainRouter` collapses
  to a single box (see `same_language`).
- **LLM calls** use `langchain_openai.ChatOpenAI` against an OpenAI-compatible endpoint
  (`base_url` + `llm_model_name` from env), imported lazily inside the endpoint functions
  in `main.py` (summary, translate-to-English, PDF generation). Keep this lazy-import
  pattern so the app still boots when LangChain/OpenAI aren't configured.
- **Graceful optional dependencies**: Azure and LLM features degrade instead of crashing
  (e.g. `AZURE_AVAILABLE` flag, `_PDF_STORE` in-memory PDF fallback with 5-min TTL).
  Preserve this "feature-off but app-up" behavior when adding integrations.
- **Indic text handling**: use `smart_join` / `is_indic_char` from `models.py` when
  concatenating streamed tokens — don't naively add spaces, which breaks Indic scripts.
- **Recordings**: conversations save as JSON (original + per-language views) into
  `backend/recordings/` via `RecordingManager`; this dir is git-ignored.
- Database is **read-mostly against pre-existing tables**; do not add table-creation
  migrations for `pces_users`/`patient`.
