# Devpost submission draft — SCRAPSHIFT

## Project name
**SCRAPSHIFT — The Waste-to-Prototype Compiler**

## One-line pitch
An inventory-first circular design tool that turns salvaged electronics into reuse-first project blueprints and records environmental outcomes only after a build is completed.

## Inspiration
Student labs and makerspaces often have boxes of old boards, sensors, cables, LEDs, and enclosures. The parts are not always worthless; they are just unidentified, untested, or disconnected from a useful project. Meanwhile, makers tend to design around a shopping list and buy new components. We wanted to reverse that default: start with the material already available and let it influence what gets built next.

## What it does
SCRAPSHIFT lets a maker catalogue salvaged electronic parts, label their condition and verification state, and choose one of five safe low-voltage starter projects. Its deterministic matching engine creates a reuse-first bill of materials that distinguishes verified matches, substitutes that need human compatibility checks, parts that need bench testing, and items that are still missing. When a prototype has actually been built and tested, the maker can record the components reused; the system decrements stock and adds a traceable event to an environmental-impact ledger.

Optional vision-assisted intake suggests component identity and tags from a photo, but it never marks a part verified. An inventory-aware assistant helps makers explore low-waste project goals. Both provider-backed AI capabilities are optional: core inventory, planning, stock accounting and reporting work without a model API key.

## How we built it
- **Frontend:** React, Vite, Bootstrap, Recharts and Lucide icons.
- **Backend:** FastAPI, Pydantic and SQLite.
- **Planning:** Transparent rule-based matching over category, part name, tags, verification status, condition and available quantity. Allocations prevent inventory from being promised to multiple BOM lines.
- **Accounting:** Transactional build completion and component-name snapshots. Reuse mass and cost proxies use user-entered per-unit values. CO₂e is shown only when factor coverage is complete.
- **AI (optional):** A server-side OpenAI-compatible Chat Completions API for vision suggestions and conversational help.
- **Delivery:** CSV exports, API tests and a Docker setup.

## What makes it different
Most sustainability tools stop at awareness, categorization, collection, or a carbon dashboard. SCRAPSHIFT's main interaction is **reverse design**: the available recovered materials help define the project before new purchases are made. Its measurement model also avoids counting a photo scan or a proposed plan as impact; only a completed-build record changes stock and creates an event.

## Environmental benefit
The primary outcomes tracked are component mass incorporated into completed builds, a replacement-cost proxy for components reused instead of newly bought, and optional estimated CO₂e where every reused component has a known mass and documented factor. The seeded environment contains clearly labelled illustrative data for demonstrating the interface. Those placeholder factors are not claimed as validated life-cycle assessments; a real deployment should replace them with cited product environmental declarations or peer-reviewed LCA sources. Reuse does not automatically prove landfill diversion, and the counterfactual boundary should be documented.

## Challenges we ran into
The hardest product-design challenge was preserving trust: a photo can suggest what a component looks like, but it cannot certify its electrical ratings or functional condition. The app therefore separates unverified, needs-testing, verified and quarantined states and excludes quarantined stock from plans. Another challenge was preventing a planner from allocating the same part to multiple requirements. We solved that with an explicit remaining-stock allocation pass and a transactional check when the build is recorded.

## What we learned
A sustainability prototype needs a clear path from user action to a physical outcome. It is not enough to visualize a lower-impact future; the tool must change a decision, support the action, and track what really happened. We also learned to separate measured quantities, user-entered assumptions, and modelled environmental estimates rather than blending them into a single “impact score.”

## What's next
- Test the matcher with real makerspace inventories and measure whether it changes purchase decisions.
- Add datasheet links and structured compatibility rules for interfaces, voltage ranges, current draw and connector types.
- Validate carbon factors against documented product LCA/EPD sources.
- Add shared makerspace workspaces and authenticated audit trails.
- Evaluate the system on the mass and number of components successfully reincorporated into working prototypes.

## Limitations
SCRAPSHIFT is a student hackathon prototype. It is not a circuit simulator or certified electronic-design tool. Matching is conservative but not formal electrical rule checking; substitutions require human validation. The optional AI can make mistakes, and suggested identities remain unverified. Demo carbon factors are illustrative. A public deployment would require authentication and additional operational security.

## Suggested thumbnail text
**BUILD FROM WHAT YOU HAVE.**

## Suggested tags
Sustainability · Circular Economy · E-waste · AI · Education · Hardware · Climate Action

## Before submitting
- Replace or remove illustrative carbon factors if they are not supported by a source.
- Add a real video and source repository link.
- Record the physical prototype and accurately describe the components actually reused.
- Complete the team/member fields and add the final deployed URL if you deploy one.
