# ArthSetu PayBot V2 🤖💸

PayBot V2 is an autonomous, multi-domain Commerce Agent platform integrated into the ArthSetu ecosystem. It uses generative AI (Gemini 2.0 Flash) to parse user intents, execute secure transactions, and seamlessly crawl third-party platforms for real-time data using Playwright. 

This repository contains the complete **FastAPI backend** for PayBot V2. It implements a 9-layer AP2 (Agentic Payments Protocol) security architecture for safe automated financial operations.

---

## 🏗️ Architecture & Core Components

### 1. Multi-Domain Support & Real-Time Universal Search (V2 Additions)
Seamlessly parses intents for multiple domains with real-time Playwright-based crawlers:
- 🛒 **Grocery & General**: Purchase groceries, compare prices across platforms (*Blinkit, Zepto, BigBasket*).
- 🎬 **Entertainment**: Book movie tickets (*BookMyShow*).
- 🚆 **Travel**: Book train tickets (*Trainman*).
- 📱 **Telecom**: Recharge phone numbers (*Jio/Airtel*).

### 2. Smart HITL (Human-In-The-Loop) Engine
- `autonomous`: Executes payment directly without user approval (e.g., Phone recharges).
- `amount_hitl`: Approves payment only if total exceeds a predefined budget (e.g., Groceries).
- `selection_hitl`: Pauses execution mid-flow to present UI options to the user before continuing (e.g., Movie show times, Train classes).
- **Agent Sessions**: Asynchronous background session tracking, allowing seamless polling and selection pausing.

### 3. AP2 9-Layer Scope Enforcer 🛡️
The server-side security middleware implementing the full AP2 security architecture:
1. **Intent Mandate signature verification**: Validates HMAC token claims.
2. **Server-side scope enforcement**: Restricts execution to specific budgets, categories, and whitelisted merchants.
3. **HITL confirmation threshold**: Forces manual approval for transactions crossing risk limits.
4. **Prompt injection prevention**: Decouples LLM processing from deterministic backend execution.
5. **Tokenized payment execution**: Never exposes user credentials or sensitive details to the agent.
6. **Immutable audit trail**: Records kryptographically verifiable evidence of agent actions.
7. **Token budget depletion guard**: Atomic DB read preventing multi-transaction race conditions.
8. **Agent identity binding**: Tags API responses tightly down to a tracked `agent_id`.
9. **Expiry + replay protection**: Prevents MITM transaction replays and invalidates out-of-time tokens.

---

## 💻 Technology Stack
* **Web Framework**: FastAPI (Uvicorn HTTP server)
* **AI Provider**: Google GenAI (`gemini-2.0-flash`)
* **Scraping Engine**: Playwright, BeautifulSoup, lxml, asyncio
* **Database**: SQLite3 (Local, Atomic locking enabled)
* **Testing**: PyTest, Asyncio Hooks
* **Token Operations**: Python `hmac` + hashlib (SHA256) standard libs

---

## 🛠️ Setup Instructions

### 1. Prerequisites
- Python 3.11+
- API Key for Google Gemini (`GEMINI_API_KEY`)

### 2. Installation
Clone the repository and install the required dependencies:

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Install Playwright browser binaries (required for crawlers)
playwright install chromium
```

### 3. Environment Variables
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
TOKEN_SECRET=your_secure_random_string
DATABASE_PATH=arthsetu.db
```

### 4. Running the Server
Run the FastAPI development server:
```bash
python -m backend.app
```
The server will start at `http://localhost:8000`.

### 5. Running the Tests
We provide a comprehensive Pytest suite (61+ passing scenarios) covering Database Integrity, Scope Enforcement, Playwright Crawlers, V2 API endpoints, and synchronous/asynchronous Agent Loops.
```bash
python -m pytest tests/test_paybot.py -v --tb=short
```

---

## 📡 API Endpoints & `curl` Examples

### 1. Start an Agent Session (Agentic Flow)
Start an autonomous/HITL interaction by passing user input. The orchestrator will dynamically understand the intent and start executing tools.

```bash
curl -X POST http://localhost:8000/api/agent-run \
     -H "Content-Type: application/json" \
     -d '{
           "user_input": "Recharge my Jio number with the best 28-day plan under Rs.300",
           "user_id": "priya_001"
         }'
```

### 2. Check Agent Session Status
Use this to poll for when the agent is running, completed, or requires selection.
```bash
curl -X GET http://localhost:8000/api/agent-status/sess_a1b2c3d4e5f6
```

### 3. Submit Selection to Agent
When a session is in `selection_hitl` mode (e.g. Movie booking), submit the chosen `option_id`.
```bash
curl -X POST http://localhost:8000/api/agent-select \
     -H "Content-Type: application/json" \
     -d '{
           "session_id": "sess_a1b2c3d4e5f6",
           "option_id": "pvr_imax_2130"
         }'
```

### 4. Domain-Specific Universal Search (Direct Fallbacks)

**Grocery Price Comparison (Blinkit, Zepto, BigBasket)**:
```bash
curl -X GET "http://localhost:8000/api/prices/grocery?item=atta&qty=2kg"
```

**Movie Ticket Shows**:
```bash
curl -X GET "http://localhost:8000/api/movies/search?movie=inception&price_cap=400&after=21:00"
```

**Train Availability**:
```bash
curl -X GET "http://localhost:8000/api/trains/search?from_city=delhi&to_city=mumbai&budget=3000"
```

**Telecom Recharge Plans**:
```bash
curl -X GET "http://localhost:8000/api/recharge/plans?operator=jio&budget=400&days=28"
```

### 5. Intent Parsing (Direct AP2 Integration)
Parse an intent naturally without starting the agent loop immediately.
```bash
curl -X POST http://localhost:8000/api/parse-intent \
     -H "Content-Type: application/json" \
     -d '{
           "user_input": "Order 2kg atta and 1L milk under Rs.500",
           "user_id": "priya_001"
         }'
```

### 6. HITL Approval & Execution
Approve an order that went above the user-specified budget or required manual action.
```bash
curl -X POST http://localhost:8000/api/transfer-confirm \
     -H "Content-Type: application/json" \
     -d '{
           "token_id": "tok_12345abcd",
           "order_id": "ord_9876xyz",
           "hitl_token": "hitl_token_abcd1234"
         }'
```

### 7. View Immutable Audit Log
```bash
curl -X GET http://localhost:8000/api/audit-log
```

---
*Built for the ArthSetu ecosystem implementation.*
*FIN-O-HACK 2026 · ASSETS DTU · In collaboration with Paytm*
