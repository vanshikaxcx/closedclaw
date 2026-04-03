<div align="center">

# ArthSetu

### *arth = wealth · setu = bridge*

**A unified AI financial OS for India's informal economy, built for the Paytm ecosystem**

[![FIN-O-HACK 2026](https://img.shields.io/badge/FIN--O--HACK-2026-blue?style=flat-square)](https://)
[![ASSETS DTU](https://img.shields.io/badge/ASSETS-DTU-orange?style=flat-square)](https://)
[![Track 1+2](https://img.shields.io/badge/Track-1%20%2B%202-green?style=flat-square)](https://)

---

**Live Demo Link: https://closedclaw-frontend.vercel.app/**
</div>

---

## What is ArthSetu?

India has 63 million small and medium businesses. Most of them use Paytm for payments — but they have no tools to understand their cash flow, automate their tax compliance, build a credit reputation, or access working capital. And their customers have no way to use AI to shop intelligently across the Paytm merchant ecosystem.

ArthSetu fixes this. It is five AI-powered modules that share a single backend, a single database, and a single merchant graph — each independently useful, but compounding when combined.

| Module | For whom | Core function |
|---|---|---|
| **Cash Flow Brain** | SMB merchants | Predict 30/60/90-day revenue; trigger restock alerts |
| **Compliance Autopilot** | SMB merchants | Auto-categorise transactions; generate + file GST returns |
| **B2B TrustScore** | SMB merchants | Build credit reputation from UPI + POS transaction history |
| **Invoice Finance Bridge** | SMB merchants | Detect overdue invoices; route to lending; auto-repay |
| **PayBot Commerce Agent** | Consumers | Intent-based agentic shopping, booking, and payments |

---

## The Compound Flywheel

Every module feeds every other. This is not a collection of features — it is a system.

```
PayBot processes a transaction
    │
    ├──► Compliance Autopilot auto-categorises it for GST
    │         └──► GST compliance score improves
    │                   └──► TrustScore rises
    │                             └──► Larger Invoice Finance credit unlocked
    │                                       └──► Merchant stocks more inventory
    │                                                 └──► Richer catalog for PayBot
    │                                                           └──► More transactions
    │
    └──► Cash Flow Brain receives new data point
              └──► 90-day projection recalculated
                        └──► WhatsApp alert: "Clear to reorder this week"
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Frontend  (React + Tailwind)                         │
│                                                                             │
│  PayBot Chat UI  │  SMB Dashboard  │  GST Filing  │  TrustScore  │  Audit  │
└───────────────────────────────────────┬─────────────────────────────────────┘
                                        │  REST API
┌───────────────────────────────────────▼─────────────────────────────────────┐
│                       Backend API  (FastAPI / Python)                       │
│                                                                             │
│  /cashflow  /gst-draft  /gst-file  /trustscore  /invoices  /credit-offer   │
│  /parse-intent  /transfer  /transfer-confirm  /merchants  /audit-log        │
└──────┬──────────────┬──────────────────┬────────────────────────────────────┘
       │              │                  │
┌──────▼──────┐ ┌─────▼──────┐  ┌───────▼────────────────────────────────────┐
│  AI / Agent │ │  Business  │  │               Data Layer                   │
│   Layer     │ │   Logic    │  │                                             │
│             │ │            │  │  SQLite: transactions · merchants ·         │
│  Claude API │ │  Cash Flow │  │  invoices · users · tokens · audit_log ·   │
│  tool loop  │ │  GST rules │  │  trustscore_history                        │
│  Scope      │ │  TS algo   │  │                                             │
│  Enforcer   │ │  Invoice   │  │  In-memory: wallet balances                │
│  A2A Agent  │ │  scoring   │  │  Synthetic: 180-day POS dataset            │
└─────────────┘ └────────────┘  └────────────────────────────────────────────┘
```

### Tech Stack

| Component | Technology |
|---|---|
| Frontend | React 18 · Tailwind CSS · Recharts |
| Backend | FastAPI (Python 3.10+) |
| AI / LLM | Anthropic Claude API (`claude-sonnet-4-6`) |
| Database | SQLite (shared across all modules) |
| Notifications | Twilio WhatsApp Sandbox |
| Token security | Python `hmac` + `hashlib` SHA-256 |
| Payments (prototype) | In-memory wallet → Razorpay sandbox (post-hackathon) |

---

## The Five Modules

---

### Module 1 — Cash Flow Brain

> *"Ramesh runs a general store in Gurgaon. He has no idea if he can afford to restock next week."*

Cash Flow Brain reads 180 days of Ramesh's Paytm POS transaction history and predicts his next 30, 60, and 90 days of revenue. When the model detects that a restock window is approaching, it fires a WhatsApp alert.

**How it works:**

1. `generate_data.py` creates a synthetic 180-day POS dataset with realistic patterns — weekday multipliers (Friday/Saturday 1.3×), month-end salary spikes (1.2×), and ±15% random noise.
2. A 14-day rolling average forms the baseline projection, extended forward with the same seasonal multipliers.
3. Confidence intervals widen over time: ±10% at 30 days, ±18% at 60 days, ±25% at 90 days.
4. If `projected_inflow_next_7_days > current_stock_cost × 0.8`, a WhatsApp alert fires.

**API:**
```
GET /api/cashflow?merchant_id=ramesh_gurgaon_001
→ { p30: { amount, confidence }, p60: {...}, p90: {...}, daily_history: [...] }
```

**Frontend:** Recharts `LineChart` — solid line for historical, dashed with confidence band for projected. 30D / 60D / 90D toggle. Alert banner when restock window detected.

---

### Module 2 — Compliance Autopilot

> *"847 transactions. 3 need your review. Your GSTR-1 is ready to file."*

Compliance Autopilot reads every transaction in the shared database and auto-categorises it for GST — assigning HSN codes, GST rates, CGST/SGST splits, and B2B/B2C classification — then generates a ready-to-file GSTR-1 and GSTR-3B draft.

**How it works:**

1. **Keyword rule engine (primary):** Matches `raw_description` against a dictionary of 80+ common SMB product keywords. `"atta"` → HSN 1001, GST 5%. `"mobile"` → HSN 8517, GST 18%. Fast, zero API cost.
2. **Claude API fallback:** Transactions that don't match any keyword get batch-sent to Claude with a structured prompt: *"Categorise this Indian GST transaction and return JSON: { hsn_code, gst_rate, category }."* Confidence < 0.8 sets `review_flag = true`.
3. GSTR-1 tables are populated from the categorised data: Table 4 (B2B > Rs.2.5L), Table 5 (B2C interstate > Rs.2.5L), Table 7 (all other B2C aggregate).
4. `/api/gst-file` returns a mock GST reference ID (`GSTN-2026-Q1-XXXXXXXX`).

**APIs:**
```
GET  /api/gst-draft?merchant_id=...&quarter=Q1&year=2026
POST /api/gst-file  { merchant_id, quarter, year, confirmed: true }
PATCH /api/gst-update-tx  { tx_id, hsn_code, gst_rate }
```

**Frontend:** Transaction review table. Flagged rows highlighted yellow — click to edit HSN/rate inline. Summary panel: Total Taxable Value · Total CGST · Total SGST · Net Tax Liability. "File Now" button with success modal.

---

### Module 3 — B2B TrustScore

> *"Score: 74 / 100 — Good. Your GST compliance is dragging you down."*

TrustScore builds a behavioural credit reputation for every merchant from their UPI and POS transaction history — no CIBIL score required, no bank statement needed.

**Algorithm — weighted composite of 5 signals (0–100):**

| Signal | Weight | How measured |
|---|---|---|
| On-time payment rate | 30% | Payments received on/before due date |
| Payment consistency | 20% | Std deviation of inter-payment intervals (lower = better) |
| Transaction volume trend | 20% | 90-day revenue: growing (+) / flat (0) / declining (−) |
| GST compliance | 20% | Filed last 2 quarters: Yes=20 / Partial=10 / No=0 |
| Return/dispute rate | 10% | `1 − (returns / total transactions)` |

**Buckets:** 0–40 Low · 41–65 Medium · 66–80 Good · 81–100 Excellent

**APIs:**
```
GET  /api/trustscore?merchant_id=...
→ { score, bucket, components: { payment_rate, consistency, ... }, history: [...] }

POST /api/trustscore-event
{ merchant_id, event_type: "PAYMENT_RECEIVED"|"GST_FILED"|"RETURN_RAISED"|"INVOICE_OVERDUE" }
```

**Frontend:** Circular gauge (colour-coded by bucket). Component breakdown bars. History sparkline.

---

### Module 4 — Invoice Finance Bridge

> *"You have a Rs.45,000 invoice overdue by 18 days. We can advance Rs.40,500 now."*

Invoice Finance Bridge detects overdue invoices, checks the seller's TrustScore, and generates a credit offer automatically. When the buyer eventually pays, the advance is auto-deducted before crediting the seller.

**Credit offer logic:**

| TrustScore | Advance % | Max advance |
|---|---|---|
| 81–100 (Excellent) | 90% | Rs. 5,00,000 |
| 66–79 (Good) | 80% | Rs. 2,00,000 |
| 41–65 (Medium) | 70% | Rs. 75,000 |
| < 40 (Low) | No offer | — |

**Detection:** Any invoice with `status = "UNPAID"` and `due_date < today − 15 days` is flagged as overdue. If TrustScore ≥ 50, a credit offer is generated.

**Repayment:** When `/api/transfer` receives a payment from `buyer_id` matching a financed invoice, the advance is auto-deducted and `repaid = true` is set.

**APIs:**
```
GET  /api/invoices?merchant_id=...
POST /api/credit-offer  { merchant_id, invoice_id }
POST /api/credit-accept { offer_id, merchant_id }
```

**Frontend:** Invoice table with status badges (PAID green · PENDING blue · OVERDUE red). "Get Advance" button on overdue rows. Credit offer modal with amount, fee, repayment terms.

---

### Module 5 — PayBot Commerce Agent

> *"Order 2kg atta, 1L milk, and recharge my Jio Rs.239 — keep it under Rs.600."*
> *Agent: Done. Rs.452 spent. Budget remaining: Rs.148. 2 tasks completed.*

PayBot is the consumer-facing agentic payment layer. It is the most technically complex module and the centrepiece of the Track 1 submission.

#### How PayBot works

A user types a natural language intent. PayBot runs a 5-agent pipeline:

```
1. Intent Parser Agent    — Claude API call #1
                            NL → structured intent JSON
                            generates Scoped Delegation Token

2. Orchestrator Agent     — Claude API call #2 (tool loop)
                            drives: search → compare → order → pay

3. Shopping Agent         — executes tool calls:
                            search_merchants · prepare_order · check_balance

4. Scope Enforcer         — FastAPI dependency (security gate)
                            9-layer validation before any payment

5. A2A Payment Agent      — isolated execution
                            /api/transfer · wallet debit · audit log
```

#### The 9-Layer Security Architecture

| # | Layer | Implementation |
|---|---|---|
| 1 | **Scoped Delegation Token** | Budget cap · categories · merchant whitelist · TTL — HMAC-SHA256 signed |
| 2 | **Server-side scope enforcement** | Every `/api/transfer` validated before touching wallet |
| 3 | **Human-in-the-Loop (HITL)** | Agent-decided: preference tasks show options; deterministic tasks auto-execute |
| 4 | **Prompt injection prevention** | User NL and merchant data in completely separate Claude API calls |
| 5 | **Tokenized payment execution** | A2A Agent receives only `token_id` + `order_id` — never user credentials |
| 6 | **Immutable audit trail** | SQLite triggers block any UPDATE or DELETE on `audit_log` |
| 7 | **Atomic budget reads** | `BEGIN EXCLUSIVE` on every spend check — TOCTOU-safe |
| 8 | **Agent identity binding** | `agent_id` in every Claude API call — new fraud signal per AP2 §7.4 |
| 9 | **Replay protection** | `tx_ids_used[]` array prevents double-charging the same order |

#### HITL Decision Logic

PayBot does not use a fixed Rs.200 threshold. It classifies query type:

- **Deterministic** — `"Recharge Jio Rs.239"` → one correct answer → auto-executes
- **Preference** — `"Book Inception tickets after 9pm under Rs.400"` → multiple valid shows → agent presents options → user picks → pays

#### AP2 Protocol Alignment

PayBot's security model is directly inspired by Google's [Agent Payments Protocol](https://ap2-protocol.org/) (backed by Visa, Mastercard, PayPal, Adyen, 60+ organisations):

| AP2 concept | PayBot implementation |
|---|---|
| Intent Mandate (VDC) | Scoped Delegation Token — HMAC-SHA256 signed JSON |
| Cart Mandate | Order object with merchant signature field |
| Payment Mandate | Audit log entry with SHA256 payload hash |
| Role-based architecture | 5 isolated micro-agents with separate security contexts |
| Non-repudiable audit | SQLite triggers prevent any mutation of `audit_log` |

#### MCP Tool Definitions

| Tool | Description | Returns |
|---|---|---|
| `search_merchants` | Find merchants selling specific items | `merchants[]` with catalog + prices |
| `prepare_order` | Build line-item order from catalog | `{ order_id, line_items[], total }` |
| `check_balance` | Get wallet balance before committing | `{ balance_inr }` |
| `request_payment` | Initiate payment — triggers HITL if preference task | `{ status, hitl_token? }` |
| `confirm_payment` | Execute after HITL approval | `{ tx_id, receipt }` |
| `get_audit_log` | Session action history | `{ log_entries[] }` |

---

## Demo Walkthrough

### Merchant view (Ramesh's dashboard)

| Step | What happens | Module |
|---|---|---|
| 1 | Open merchant dashboard | Cash Flow Brain chart loads · TrustScore panel visible |
| 2 | WhatsApp alert fires | "Stock reorder week starts in 3 days. Expected inflow: Rs.56,000." | Cash Flow Brain |
| 3 | GST Filing screen | "847 transactions auto-categorised. 3 need review." | Compliance Autopilot |
| 4 | Review 3 flagged transactions | Edit HSN codes inline · tap "File Now" · GST ref ID shown | Compliance Autopilot |
| 5 | Invoice Finance panel | Overdue invoice Rs.45,000. Tap "Get Advance" → Rs.40,500 offered | Invoice Finance |
| 6 | Accept advance | "Advance on its way. Expected in 4 hours." WhatsApp confirmation | Invoice Finance |

### Consumer view (Priya's PayBot)

| Step | What Priya types / sees | What the agent does |
|---|---|---|
| 1 | *"Order 2kg atta, 1L milk, recharge Jio Rs.239 — under Rs.600"* | — |
| 2 | Intent Card: 3 items · Rs.600 cap · grocery + telecom · 2hr validity | Claude API call #1: NL → structured intent |
| 3 | Token Badge activates: Budget Rs.600 · 2hr · Active | Scoped Delegation Token generated + HMAC signed |
| 4 | Agent Steps Feed: "Searching merchants... Found Ramesh General Store: Rs.213..." | Claude API tool loop: search → prepare_order |
| 5 | HITL Modal: "Approve Rs.213 to Ramesh General Store? 28 seconds remaining" | Amount > Rs.200 → Scope Enforcer triggers HITL |
| 6 | Priya taps Approve | `/api/transfer-confirm` → Scope Enforcer → A2A Payment Agent → wallet.py |
| 7 | "Jio recharge completed (auto-executed — below threshold)" | Rs.239 < HITL threshold → deterministic → auto |
| 8 | Receipt: "2 tasks. Rs.452 spent. Budget remaining: Rs.148." | Audit log written · `budget_spent` updated atomically |
| 9 | Switch to Ramesh's dashboard | Rs.213 now visible in his transactions · TrustScore updated |
| 10 | Audit Log panel | Complete cryptographic log of every agent action in the session |

---

## Project Structure

```
arthsetu/
│
├── backend/
│   ├── main.py                    # FastAPI app — registers all routers
│   ├── db.py                      # SQLite schema init + seed script
│   ├── wallet.py                  # In-memory wallet + /api/transfer
│   ├── audit.py                   # Append-only audit log (SQLite triggers)
│   ├── whatsapp.py                # Twilio WhatsApp Sandbox integration
│   │
│   ├── data/
│   │   ├── merchants.json         # Seeded merchant catalog (6 merchants)
│   │   ├── seed_data.py           # DB seed script
│   │   └── generate_data.py       # 180-day synthetic POS dataset generator
│   │
│   └── modules/
│       ├── cashflow.py            # Module 1 — Cash Flow Brain router
│       ├── compliance.py          # Module 2 — Compliance Autopilot router
│       ├── trustscore.py          # Module 3 — TrustScore router
│       ├── invoice.py             # Module 4 — Invoice Finance router
│       └── paybot/
│           ├── paybot.py          # Module 5 — PayBot router
│           ├── orchestrator.py    # Claude API tool loop
│           ├── intent_parser.py   # Claude API call #1 — NL → intent
│           ├── token.py           # Scoped token CRUD + HMAC signing
│           ├── scope_enforcer.py  # FastAPI dependency — 9-layer enforcement
│           ├── shopping_agent.py  # search_merchants + prepare_order
│           ├── payment_agent.py   # A2A isolated payment execution
│           ├── hitl.py            # HITL order management + 30s timer
│           └── tools.py           # MCP tool definitions
│
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── pages/
│       │   ├── MerchantDashboard.jsx   # Ramesh's SMB dashboard
│       │   └── ConsumerView.jsx        # Priya's PayBot chat
│       └── components/
│           ├── CashFlowChart.jsx       # Recharts projection chart (Module 1)
│           ├── GSTFilingScreen.jsx     # Transaction review + file (Module 2)
│           ├── TrustScorePanel.jsx     # Circular gauge + breakdown (Module 3)
│           ├── InvoiceTable.jsx        # Invoice list + advance (Module 4)
│           ├── PayBotChat.jsx          # Root chat component (Module 5)
│           ├── IntentCard.jsx          # Parsed intent display
│           ├── TokenBadge.jsx          # Live budget + expiry
│           ├── AgentStepsFeed.jsx      # Tool call narration stream
│           ├── HITLModal.jsx           # Human approval modal + timer
│           ├── ReceiptScreen.jsx       # Transaction receipt
│           └── AuditLog.jsx            # Agent action history table
│
├── .env.example
├── requirements.txt
└── README.md
```

---

## Quickstart

### Prerequisites

- Python 3.10+
- Node.js 18+
- Twilio account — free trial, WhatsApp Sandbox (20-minute setup)

### 1. Clone and configure

```bash
git clone https://github.com/your-team/arthsetu
cd arthsetu
cp .env.example .env
# Edit .env — fill in your keys (see below)
```

### 2. Backend setup

```bash
cd backend
pip install -r requirements.txt
python db.py                  # initialise SQLite schema + seed demo data
python data/generate_data.py  # generate 180-day synthetic POS dataset
uvicorn main:app --reload --port 8000
```

### 3. Frontend setup

```bash
cd frontend
npm install
npm start                     # http://localhost:3000
```

### Environment variables

```bash
# Required
GEMINI_API_KEY=sk-ant-...

# Twilio WhatsApp (optional for local dev — UI falls back to simulated alert)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
DEMO_PHONE=whatsapp:+91XXXXXXXXXX

# Config
HITL_THRESHOLD=200            # Rs. amount above which HITL modal triggers
DATABASE_URL=sqlite:///arthsetu.db
REACT_APP_API_URL=http://localhost:8000
```

---

## API Reference

### Shared endpoints (Team E)

| Endpoint | Method | Description |
|---|---|---|
| `/api/merchants` | GET | All registered merchants with full product catalog |
| `/api/transfer` | POST | Execute wallet transfer (scope-enforced) |
| `/api/check-balance` | GET | User wallet balance |
| `/api/audit-log` | GET | All agent action log entries |
| `/api/whatsapp-alert` | POST | Send WhatsApp notification via Twilio |

### Cash Flow Brain (Module 1)

| Endpoint | Method | Description |
|---|---|---|
| `/api/cashflow` | GET | 30/60/90-day cash flow projections for a merchant |

### Compliance Autopilot (Module 2)

| Endpoint | Method | Description |
|---|---|---|
| `/api/gst-draft` | GET | GSTR-1 + GSTR-3B draft for a merchant + quarter |
| `/api/gst-file` | POST | File the draft (mock — returns GST reference ID) |
| `/api/gst-update-tx` | PATCH | Manually correct HSN code or GST rate on a transaction |

### B2B TrustScore (Module 3)

| Endpoint | Method | Description |
|---|---|---|
| `/api/trustscore` | GET | Score, component breakdown, and history for a merchant |
| `/api/trustscore-event` | POST | Push a score-affecting event from any module |

### Invoice Finance Bridge (Module 4)

| Endpoint | Method | Description |
|---|---|---|
| `/api/invoices` | GET | All invoices for a merchant with status + advance info |
| `/api/credit-offer` | POST | Generate a credit offer for an overdue invoice |
| `/api/credit-accept` | POST | Accept offer — disburses advance, updates invoice status |

### PayBot Commerce Agent (Module 5)

| Endpoint | Method | Description |
|---|---|---|
| `/api/parse-intent` | POST | NL → structured intent JSON + scoped delegation token |
| `/api/transfer-confirm` | POST | Execute payment after HITL approval |
| `/api/token-status` | GET | Live budget remaining + seconds until expiry |
| `/api/agent/search-merchants` | POST | Find merchants by item list (whitelist-checked) |
| `/api/agent/prepare-order` | POST | Build line-item order from merchant catalog |
| `/api/agent/check-balance` | GET | Wallet balance read (token-gated) |

---

## Database Schema

```sql
merchants         -- merchant_id, name, category, location, paytm_pos_id
products          -- product_id, merchant_id, name, price, hsn_code, gst_rate, stock_qty
users             -- user_id, name, phone, wallet_balance
transactions      -- tx_id, merchant_id, user_id, amount, timestamp, gst_category, hsn_code
invoices          -- invoice_id, seller_id, buyer_id, amount, due_date, status, advance_amount
tokens            -- token_id, user_id, agent_id, budget_cap, budget_spent, categories (JSON),
                  --   valid_until, tx_ids_used (JSON), status, signature
audit_log         -- log_id, timestamp, token_id, agent_id, action_type, entity_id,
                  --   amount, outcome, payload_hash (SHA256)
trustscore_history -- record_id, merchant_id, score, components (JSON), computed_at
```

The `audit_log` table is append-only — SQLite triggers reject any `UPDATE` or `DELETE` attempt at the database level.

---

## Merchant Catalog (Seeded Demo Data)

| Merchant | Category | Sample products | Agent-addressable |
|---|---|---|---|
| Ramesh General Store | Grocery | Atta Rs.145/2kg · Milk Rs.68/L · Rice Rs.95/kg | ✓ |
| Sharma Electronics | Electronics | USB Cable Rs.299 · Earphones Rs.599 | ✓ |
| Singh Pharmacy | Health | Paracetamol Rs.15 · Vitamin C Rs.120 | ✓ |
| Patel Mobile Recharge | Telecom | Jio Rs.239 · Airtel Rs.299 · Vi Rs.179 | ✓ |
| Gupta Clothing Store | Clothing | T-Shirt Rs.350 · Jeans Rs.899 | ✓ |
| Kumar Sweet Shop | Food | Barfi 500g Rs.280 · Ladoo 500g Rs.320 | ✓ |

---

## How Paytm Integrates This

ArthSetu is a concept built specifically for Paytm to integrate into their existing platform. The integration story is technically clean — Paytm replaces only the data sources, not the intelligence.

| What ArthSetu uses (hackathon) | What Paytm replaces it with | Effort |
|---|---|---|
| Hardcoded merchant JSON | Paytm for Business registry (tens of millions of merchants) | API swap |
| 180-day synthetic POS data | Real Paytm POS transaction history | Data pipe |
| In-memory wallet | Paytm Wallet + UPI rails (already live) | API swap |
| Mock GST filing | Actual GST Portal API via GSTN sandbox | API swap |
| Simulated recharge catalog | Paytm's existing operator/recharge API (already live) | Already exists |
| Invoice lending mock | Paytm Lending arm underwriting (NBFC partner) | Partnership |
| Gemini API intent parsing | Same — or fine-tuned model on Paytm transaction data | Unchanged |
| Scope Enforcer security | Same — upgraded to full AP2 VDC with Ed25519 signatures | Upgrade path |

The agent layer, comparison engine, security architecture, and audit trail require zero changes.

---




**FIN-O-HACK 2026 · ASSETS DTU · In collaboration with Paytm · April 2026**

---

## Tracks

- **Track 1** — PayBot Commerce Agent (Module 5): intent-based agentic payments with 9-layer security
- **Track 2** — Cash Flow Brain · Compliance Autopilot · TrustScore · Invoice Finance (Modules 1–4): AI financial OS for SMB merchants

Both tracks share a single codebase, a single database, and a single integration layer.

---

<div align="center">

*ArthSetu — Building the bridge between India's informal economy and its financial future.*

</div>
