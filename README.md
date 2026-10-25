# SCRAPSHIFT — The Waste-to-Prototype Compiler

> **Don't buy parts for your next invention. Build it from yesterday's waste.**

SCRAPSHIFT is a circular-hardware design workspace for students, makerspaces, electronics labs, and repair communities. Instead of designing a project first and buying a bill of materials afterward, a maker inventories salvaged components and receives a reuse-first design plan. The product distinguishes verified parts from parts that need testing, flags missing materials, and records environmental outcomes only after the maker logs a completed build.

## Why this exists

Recoverable components can sit unused because nobody knows what they are, whether they work, or what they could help build. Conventional project planners start with a shopping list. SCRAPSHIFT reverses the workflow:

1. **Inventory before ideation.** Record salvaged components, condition, source, quantity, known specifications, replacement price, and optional sourced impact factors.
2. **Design around available stock.** A transparent rules engine matches a project template to available parts, avoids double-allocating stock, and separates verified matches, test-needed parts, substitutions, and missing items.
3. **Build safely.** Quarantined parts never enter suggestions. Unverified parts cannot be logged as reused in a completed build. The UI reminds makers to check pinouts, ratings, insulation, and current limiting.
4. **Measure what actually happened.** Only a completed-build record changes stock or writes an impact event. Plan-stage estimates are not counted as achieved impact.

## Features

### 1. Inventory workspace
- Create, edit, verify, search, filter, and remove component records.
- Track stock quantity, source, condition, mass, voltage, interface, tags, replacement-cost proxy, and optional embodied-carbon factor/source.
- Keep components in `unverified`, `needs_testing`, `verified`, or `quarantined` states.
- Quarantined records are excluded from every project plan.
- Export the full inventory as CSV.
- Optional vision-assisted image intake can suggest a component's identity and tags when an OpenAI-compatible API key is configured. Its result is always left unverified.

### 2. Reuse-first build planner
- Five curated starter blueprints: soil moisture monitor, indoor mini weather station, low-voltage plant watering helper, low-voltage desk light, and motion notifier.
- Auto-match simple free-text project goals to the closest starter blueprint.
- Rules-based component matching using category, name, type, tags, condition, and verification state.
- Greedy stock allocation prevents the same physical inventory from being promised to two BOM lines.
- Verified stock, substitutions, needs-testing items, and missing quantities are explained separately.
- Buildability and inventory-coverage scores distinguish verified readiness from provisional matches.
- Generates practical inspection and bench-test steps.

### 3. Completed-build and impact ledger
- A completed build can only log **verified** component stock, validates quantity, and decrements inventory within a SQLite transaction.
- Stores historical component-name snapshots so later inventory edits do not rewrite the build's record.
- Tracks reused component units, recorded reuse mass, replacement-cost proxy, factor coverage, and emissions estimates only when factor coverage is complete.
- Explicitly labels seeded examples as demo data.
- Exports the impact ledger as CSV.

### 4. Circular assistant
- Inventory-aware local rules mode works without a paid AI key.
- If configured, an optional AI assistant can help frame projects, and a multimodal endpoint can suggest fields from a component photo.
- Safety restrictions are included in prompts and UI guidance; model suggestions never automatically mark a component as verified.

### 5. Operational quality
- React + Vite + Bootstrap frontend, responsive desktop/tablet/mobile layout, charts, status badges, forms, error states, and toasts.
- FastAPI + Pydantic + SQLite backend.
- CSV export endpoints, API validation, database transactions, automated service/API tests, Docker image and Compose setup.
- Local-first default: the database stays on the machine running the backend.

## Architecture

```text
┌─────────────────────────────────────────────┐
│ React + Vite + Bootstrap                    │
│ Dashboard · Inventory · Planner · Impact    │
│ History · Circular Assistant                │
└──────────────────────┬──────────────────────┘
                       │ /api
┌──────────────────────▼──────────────────────┐
│ FastAPI                                     │
│ Inventory API · Templates · Plans           │
│ Completed builds · CSV exports · Optional AI│
└────────────┬───────────────────┬────────────┘
             │                   │
┌────────────▼──────────┐  ┌─────▼─────────────────┐
│ SQLite repository     │  │ Matching / impact     │
│ Components · Builds   │  │ Rules engine          │
│ Build parts · Events  │  │ Transparent formulas  │
└───────────────────────┘  └───────────────────────┘
```

### Main directories

```text
scrapshift/
├── backend/
│   ├── app/
│   │   ├── main.py          # REST API and optional AI endpoints
│   │   ├── database.py      # SQLite schema and demo seed data
│   │   ├── schemas.py       # Request/response validation
│   │   ├── matcher.py       # Inventory matching and readiness scoring
│   │   ├── impact.py        # Environmental metric calculations
│   │   └── templates.py     # Curated low-voltage project blueprints
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── styles.css
│   │   └── components/      # Inventory, planner, dashboard, ledger, assistant
│   ├── package.json
│   └── vite.config.js
├── docs/
│   ├── DEMO_SCRIPT.md
│   ├── DEVPOST_SUBMISSION.md
│   ├── IMPACT_METHODOLOGY.md
│   └── API_REFERENCE.md
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Run locally

### Requirements

- Python 3.11+ (Python 3.12 recommended)
- Node.js 20+ and npm
- The first install requires package access to download Python and npm dependencies.
- An AI API key is optional. The core application does not require it.

### Start the backend

**macOS / Linux**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

**Windows PowerShell**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`

The database is created at `backend/data/scrapshift.db` on first startup. It is seeded with a clearly marked demo workspace. Keep `SCRAPSHIFT_ENABLE_DEMO_RESET=true` only for local development; resetting deletes all records in that local database and restores the demo data.

### Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5173`. Vite proxies `/api` to `http://localhost:8000`.

### Optional AI setup

Edit `backend/.env`:

```dotenv
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://api.openai.com/v1/chat/completions
OPENAI_MODEL=gpt-4o-mini
```

Restart the backend after changing environment variables. Keep keys server-side; never put provider keys in Vite's `VITE_*` variables. Vision recognition and the AI assistant are optional provider-backed features; inventory, deterministic planning, build logging, CSV export, and impact reporting work without a key.

`OPENAI_BASE_URL` must be a Chat Completions-compatible endpoint. The AI model's component scan is a suggestion and is never authoritative identification.

## Docker

Build and run the full app as one service:

```bash
docker compose up --build
```

Open `http://localhost:8000`. SQLite data persists in the `scrapshift_data` named volume. The container sets `ENVIRONMENT=production` and disables the destructive demo reset endpoint. Add an `OPENAI_API_KEY` to the environment only if you want the optional provider-backed AI features.

## Tests

From the `backend/` directory:

```bash
PYTHONPATH=. pytest -q
```

PowerShell:

```powershell
$env:PYTHONPATH = "."
pytest -q
```

Tests cover template inference, mass/cost/carbon arithmetic, uncertainty handling, quarantined-part exclusion, inventory/planner endpoints, and stock deduction during build completion.

## Environmental-accounting rules

- **Inventory is not impact.** Scanning, tagging, or planning around a component does not count as reuse.
- **Completed builds create impact events.** The maker confirms that a prototype was physically built, then the server deducts verified stock and records the reuse event.
- **Reuse mass** is the sum of entered per-unit masses times the quantities logged. Missing mass values are unknown, not zero.
- **Replacement-cost proxy** is user-entered estimated new-purchase cost for the reused quantity. It is not audited cash savings.
- **CO₂e** is only reported for a build when each reused component has a mass and an embodied-carbon factor. Users must enter the factor source. The seeded values are intentionally marked *demo-only illustrative estimate* and must be replaced with cited LCA/EPD values before being used as factual claims.
- Do not claim that recorded reuse automatically means landfill diversion or avoided emissions. The physical disposal counterfactual and impact boundary need to be documented for a serious evaluation.

See [`docs/IMPACT_METHODOLOGY.md`](docs/IMPACT_METHODOLOGY.md) for reporting guidance.

## Safety and limitations

SCRAPSHIFT is a student hackathon prototype, not a certified electronic-design or repair tool. Only prototype low-voltage projects. Never harvest or disassemble lithium-ion batteries, swollen batteries, mains adapters, CRTs, capacitors with unknown charge state, or hazardous e-waste. Use qualified handlers for hazardous devices. Check official component datasheets, pinouts, voltage/current ratings, isolation, and insulation. An `verified` state is a maker's recorded test status, not independent certification.

The starter projects and matching rules are intentionally curated and conservative; they do not perform circuit simulation, formal electrical rule checking, or automatic PCB design. The local assistant's inferred template is a best-effort heuristic, and substitutions require human engineering judgment.

## Privacy and deployment

- By default this is a single-workspace local prototype with no user accounts or authentication.
- Do not place sensitive inventories or API secrets in a publicly accessible instance.
- Before exposing the service to the public internet, add authentication/authorization, rate limits, HTTPS, request quotas, backup/restore controls, a protected administrative reset flow, and stronger audit controls. Disabling the reset endpoint alone does not secure the rest of the API.
- `backend/.env`, SQLite data, and build artifacts are excluded from source control.

## License

MIT. See [`LICENSE`](LICENSE).
