# Deploying `closedclaw` on Vercel (Frontend + Backend)

This repo is best deployed as **two Vercel projects**:

1. **Backend project** (FastAPI): repo root `closedclaw`
2. **Frontend project** (Next.js): root directory `paytm ui`

This keeps the architecture stable and lets frontend `/api/*` calls proxy cleanly to backend.

## 1) Deploy backend (FastAPI)

### Vercel project settings
- Framework Preset: **Other**
- Root Directory: **`.`** (repo root)
- Build Command: *(leave empty)*
- Output Directory: *(leave empty)*
- Install Command: *(leave empty, Vercel uses `requirements.txt` for Python functions)*

### What is already configured
- `api/index.py` exports the FastAPI app for Vercel runtime.
- `vercel.json` sets Python runtime (`python3.12`) and function timeout.
- `requirements.txt` includes backend dependencies.

### Backend environment variables
Set these in Vercel → Project → Settings → Environment Variables (use values for your setup):

- `APPWRITE_ENDPOINT`
- `APPWRITE_PROJECT_ID`
- `APPWRITE_API_KEY`
- `APPWRITE_DATABASE_ID`
- `APPWRITE_MERCHANTS_COLLECTION_ID`
- `APPWRITE_TRANSACTIONS_COLLECTION_ID`
- `APPWRITE_INVOICES_COLLECTION_ID`
- `APPWRITE_CREDIT_OFFERS_COLLECTION_ID`
- `APPWRITE_FINANCING_LEDGER_COLLECTION_ID`
- `APPWRITE_TRUSTSCORE_HISTORY_COLLECTION_ID`
- `APPWRITE_AUDIT_LOG_COLLECTION_ID`
- `APPWRITE_NOTIFICATIONS_COLLECTION_ID`
- `APPWRITE_WHATSAPP_LOG_COLLECTION_ID`
- `APPWRITE_GST_DRAFTS_COLLECTION_ID`
- `APPWRITE_DEMO_STATE_COLLECTION_ID`
- `APPWRITE_PENDING_TRANSFERS_COLLECTION_ID`

Optional demo toggles:
- `ARTHSETU_DEMO_MODE`
- `ARTHSETU_DEMO_SEED_ON_STARTUP`
- `ARTHSETU_ENABLE_DEMO_RESET`

Optional messaging/AI keys if those routes are used:
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`
- `GEMINI_API_KEY`, `MISTRAL_API_KEY`, `GROQ_API_KEY`

After deployment, note backend URL, e.g.:
- `https://closedclaw-backend.vercel.app`

Health check:
- `https://closedclaw-backend.vercel.app/api/health`

## 2) Deploy frontend (Next.js)

### Vercel project settings
- Framework Preset: **Next.js**
- Root Directory: **`paytm ui`**
- Build Command: `npm run build`
- Install Command: `npm install`

### Frontend environment variables
Set these in Vercel → Project → Settings → Environment Variables:

- `NEXT_PUBLIC_ADAPTER_MODE=live`
- `NEXT_PUBLIC_API_URL=https://<your-backend-vercel-domain>`
- `BACKEND_API_URL=https://<your-backend-vercel-domain>`

`BACKEND_API_URL` is used by `paytm ui/next.config.mjs` rewrite so frontend calls like `/api/trustscore` are proxied to backend.

## 3) Domain wiring and verification

1. Deploy backend first.
2. Add backend URL env vars to frontend project.
3. Redeploy frontend.
4. Verify from browser/network tab that frontend calls `/api/*` and responses are successful.

Quick checks:
- Frontend home loads.
- Merchant pages fetch trust score/invoices.
- `GET /api/health` returns `{ "status": "ok", ... }`.

## Notes

- Root `.vercelignore` is tuned for backend deployment and excludes the large frontend folder from backend upload.
- If you later want a single-project deployment, it will need a different routing/build strategy than this two-project production setup.
