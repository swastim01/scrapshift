# SCRAPSHIFT demo script (90–120 seconds)

## Demo objective
Show judges a complete chain from salvaged parts to a working design decision to recorded reuse. Emphasize that SCRAPSHIFT optimizes for a completed reuse outcome, not the number of items scanned.

### Scene 1 — The problem (0:00–0:12)
**On screen:** SCRAPSHIFT dashboard and seed data label.

**Say:** “Engineering labs and student makers often buy parts for every new prototype while usable components sit in drawers. Most tools help list, sort, or collect waste. SCRAPSHIFT reverses the design process: start from the components you already have.”

### Scene 2 — Inventory with verification (0:12–0:28)
**On screen:** Inventory page; search “sensor”; open the capacitive soil moisture sensor; point to mass, condition, source, status, and tags. Optionally add a real component manually.

**Say:** “Every component has a quantity, source, known specs, and a clear verification state. A scanned photo can suggest an identity, but it stays unverified until a person checks it. Quarantined components are kept out of plans.”

### Scene 3 — Reverse design (0:28–0:55)
**On screen:** Build planner → Soil moisture monitor → generate circular design. Show verified matches, needs-testing parts, and missing items separately. Click “Mark tested” on a part only if a real bench test has been performed.

**Say:** “Instead of generating a shopping list first, SCRAPSHIFT matches a project against the inventory. It allocates stock once, surfaces test-needed parts, and tells the maker exactly what is missing. The core compatibility engine is deterministic, so the demo works without a paid model API.”

### Scene 4 — Prove reuse (0:55–1:16)
**On screen:** Physical prototype or actual completed build; enter notes and any new parts purchased; confirm completed build.

**Say:** “Once the prototype is physically built and tested, the maker logs only the verified parts actually reused. The backend validates quantities in a transaction, deducts consumed stock, and writes an immutable-ish snapshot of the completed build.”

**Important:** Do not log a build as completed solely to create a metric. For the video, use a real tested low-voltage prototype. If no physical build has been made, narrate this step without submitting the form and label screenshots/data as illustrative.

### Scene 5 — Impact integrity (1:16–1:35)
**On screen:** Impact ledger → reused mass, replacement-cost proxy, factor coverage, export CSV. Click a sample row to point out “Sample data.”

**Say:** “The ledger reports recorded reuse mass and a replacement-cost proxy. It reports CO₂e only when each logged part has a known mass and factor. Seed values are labelled demo assumptions—not authoritative lifecycle-assessment results. That prevents a scan count from being presented as environmental impact.”

### Scene 6 — Closing (1:35–1:45)
**On screen:** Dashboard / tagline.

**Say:** “SCRAPSHIFT helps students build useful things with materials already in circulation. The goal isn’t to scan more waste. It’s to successfully reuse more of it.”

## Recording checklist
- Use the seeded demo workspace only to explain navigation; call out all sample entries explicitly.
- If demonstrating photo recognition, configure the optional API key before recording and show the result staying unverified.
- Show at least one physical part and the actual prototype if available.
- Do not show a carbon number as a validated saving unless you have a documented factor and boundary.
- Show `/docs` briefly only if judges care about the implementation; prefer the product flow.
- Record a 1080p video with the browser zoom set so status labels remain readable.
