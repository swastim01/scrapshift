# Impact methodology and claims policy

SCRAPSHIFT intentionally separates three kinds of information:

1. **Inventory facts supplied by a maker:** component name, quantity, condition, mass, interface, replacement price, and source.
2. **Recorded reuse outcomes:** a component is consumed from inventory only when the maker logs a completed build and the server verifies stock and verification status.
3. **Modelled environmental estimates:** replacement cost and CO₂e calculations derived from inputs and factors. These are not measurements of real-world emissions.

## Metrics

### Reuse mass
For every component line in a completed build:

`reuse mass (g) = component mass per unit (g) × quantity recorded`

Total reuse mass is the sum across component lines. Unknown component masses are not assumed to be zero in the product copy, but the current numerical sum only includes entries with a supplied mass. A serious public report should disclose how much of the reused inventory has a known mass.

### Replacement-cost proxy

`replacement cost proxy (INR) = estimated new-purchase price per unit × quantity reused`

This approximates the value of purchases that might be avoided if the reused components served the same function. It is not a cash saving, proof of purchase intent, or validated market valuation. Actual buying behavior should be studied separately.

### Estimated embodied CO₂e

`estimated CO₂e (kg) = sum(embodied-carbon factor per unit × quantity reused)`

The app only reports a build-level CO₂e value if every reused component has a recorded mass and entered factor. Each factor should cite its product boundary and source (preferably product EPD, peer-reviewed LCA, or a suitably specific published dataset). Similar components may differ significantly by product, size, region, manufacturing energy mix, and lifecycle boundary.

Seeded factors are labelled **“Demo-only illustrative estimate; replace with a cited LCA factor.”** They exist solely to exercise the UI. They are not citations, not authoritative emissions factors, and not suitable for a real impact claim. Replace them before recording any environmental result for external use.

## What we do not claim

- A scanned item equals waste prevented.
- A part in inventory equals a successfully reused part.
- Reuse mass automatically equals landfill diversion.
- A purchase-cost proxy equals money saved.
- A carbon estimate without a documented factor is zero CO₂e.
- AI vision can determine exact ratings or functional condition from an image.

## Evidence to collect in a real pilot

- Baseline inventory and source of each salvaged component.
- Photos or test logs showing condition and basic functional verification.
- Project BOM before and after reuse-first planning.
- Actual quantities reused, new parts purchased, and whether the project functioned.
- Evidence of a real purchase avoided, if making a purchase-avoidance claim.
- Factor citation, units, conversion method, system boundary, and a note on uncertainty.
- For diversion claims, the plausible disposal or recycling counterfactual and its evidence.

The strongest pilot outcome is not the number of users who scanned a component; it is the number and mass of salvaged parts that were incorporated into working builds, with a documented counterfactual.
