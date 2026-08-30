# Readiness, budget, food, and bookings

Use `readiness.yaml` for entry/transit, health/medication, insurance, transport, lodging, activities, dining, connectivity, money, documents, packing, emergency, and pre-departure actions. Each item needs a stable ID, status, owner when known, due/recheck time when known, source/claim links, dependencies, and a concise completion or cancellation condition. Critical unknowns remain visible actions or blockers until verified.

Use only `itinerary.yaml` `budget_items` for itemized cost. Record `exact`, `estimate`, `range`, or `unknown`; currency; per-person/per-group basis; inclusions, taxes/fees, and refundability when known. Exact/estimate uses `amount`, range uses `amount_min` and `amount_max`, and unknown has no numeric amount. Never turn unknown into zero or combine incompatible currencies/bases into a reassuring total.

Populate optional `budget_summary` only when all included arithmetic and any FX source/date are explicit. Otherwise leave it `null` and show known subtotals plus unknowns. Keep contingency as a labelled item or assumption.

Build food choices by location and day fit: propose alternatives, compare constraints and booking needs, ask the user to choose, and retain useful rejected options in decision history. Research may prepare a booking decision, but the user selects and completes every reservation, payment, or external contact.
