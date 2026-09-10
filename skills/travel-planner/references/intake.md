# Intake

Ask one consequential question at a time and save confirmed answers before moving on. Establish destination or route shape, dates and fixed events, origin, travellers, budget range/currency, pace, hard constraints, important preferences, and who decides when the group disagrees. Do not turn the first conversation into a form.

Collect traveller details only when they change the plan: anonymous ID, age group, mobility/access needs, dietary or allergy constraints, pace, luggage, driving role, interests, and exclusions. Ask citizenship or residency only for a necessary entry/transit check. Record that a medication check is required rather than collecting a diagnosis or medical record.

Keep hard constraints separate from preferences. Label assumptions and unknowns, especially dates, prices, availability, and high-stakes requirements. Create readiness actions for unknowns that can block entry, transport, lodging, or timed activities.

Save ordinary user inputs without asking for URLs. For reports such as “the hotel is paid” or planning estimates, follow the [provenance rules](research.md#user-reports-estimates-and-checked-sources): retain attribution in existing fields and distinguish a reported fact from an independent source check.

If the user explicitly asks for a quick draft, use only known inputs, show every important assumption/unknown, and attach a recheck or user-decision action. Otherwise continue collaboratively until the brief is sufficient to research useful alternatives. Both paths start with lifecycle status `draft`. A request for an HTML file, including a ready-to-share copy, keeps it `draft` until the user's explicit finalization choice under [lifecycle](verification-and-render.md#lifecycle).

## Luggage inputs

Before detailing lodging changes or activities between stays, establish the number and approximate size of bags for the group or each traveller, including bulky activity equipment. Reuse saved answers; missing luggage data means unknown, not daypacks only. A useful first question is “Сколько у вас будет чемоданов и какого примерно размера?” If forwarding could help, then establish willingness to use it and how many nights the group can manage with a small bag. Ask exact dimensions or weight only when a relevant carrier/storage limit needs them; keep essential items with the travellers.

Use the existing `brief.yaml.travelers[].luggage` object for known individual luggage, with a concise `description` such as “Per user: one large suitcase and one daypack; dimensions unknown”. This is a recording convention inside the existing free-form object, not a new schema. Record group totals with explicit group attribution in `brief.yaml.assumptions` until individual allocation is known; do not assign the whole group's bags to one traveller. Use `soft_preferences` for forwarding/handling preferences, `hard_constraints` for non-negotiable carrying needs, and `assumptions` for unresolved inputs. Turn consequential gaps into readiness actions. Brief fields do not automatically appear in HTML: repeat the relevant carrying assumption in the affected day's event `detail`.

For a quick draft, continue with explicit conditional options and an open luggage question. Do not silently choose a service before the inputs are known. Apply the [lodging transition contract](planning.md#lodging-transitions-and-luggage) when detailing the day.
