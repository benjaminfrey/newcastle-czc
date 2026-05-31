# MEMORANDUM

**To:** Newcastle Planning Board
**From:** Ben Frey  *(Article 3 code-amendment drafter)*
**Date:** May 30, 2026
**Re:** When the Code Enforcement Officer or Planning Board should require a particular cross-section component or width in the draft Article 3 Street/Road Type standards — the "everyone builds to the minimum" problem, and options to fix it
**Status:** **Discussion draft — NOT integrated into the code.** This memo presents the problem and a menu of options for the Board to discuss. No code language has been changed. Any provision sketched in §6 below is illustrative drafting only, offered to make the options concrete; it is not proposed for adoption until the Board chooses an approach.

---

## 1. The issue

The draft Article 3 calibrates each Street/Road Type with **ranges** (e.g., S1 right-of-way 66–80 ft; travel lanes 2 @ 10–11 ft; planting strip 5–8 ft) and **optional or soft components** (sidewalk "one side / optional / none"; on-street parking "optional"; planting strip "optional"; street trees "encouraged" / "permitted"). That flexibility is deliberate and good — it is the whole point of a context-based code. But flexibility with no rule about *who decides where in the range to land, and why*, has a predictable failure mode: **every new street is built to the cheapest configuration the range allows.** An applicant choosing between "sidewalk one side" and "no sidewalk," or between a 66-ft and an 80-ft right-of-way, will, absent a rule, choose the one that costs least to build — which is rarely the one that best serves the District.

Three provisions in the current draft actively steer toward the floor:

1. **§3.c.4 — "All measurements stated for a Type are minimums unless otherwise indicated."** This sentence is the root of the problem. It tells every applicant that the bottom of every range is theirs *by right*. It converts a calibrated range into a one-way ratchet toward the minimum.
2. **§3.c.2 — the value chosen within a range "must be supported by an engineering justification."** This sounds like a check, but it cuts the wrong way: an engineer can readily justify the *minimum* (it meets the safety standard at least cost). Nothing in the provision asks whether a *fuller* section would better serve the place.
3. **The soft component language itself** — "optional," "encouraged," "permitted," "where feasible." Each of these defaults to *absent*, because the absent option is always the cheaper one.

The result, left unaddressed, is that a form-based code written to produce village streets with sidewalks, street trees, and on-street parking would instead routinely produce minimum-width cartways with none of those things — the very "uniform," context-blind outcome Article 3 was written to replace.

The Board's instinct is correct: **the code needs language about when a component or a higher width may or must be required, and the reasoning that supports the requirement.** This memo lays out how to do that without (a) destroying the flexibility that makes the code work, or (b) creating open-ended discretion that is legally vulnerable.

---

## 2. Reframing — this is not "push everything to the maximum"

Before choosing a mechanism, it helps to be precise about *what* should be pushed up and *where*, because a naïve "default to the maximum" rule would be wrong on two counts.

**(a) Some dimensions are supposed to be small.** Narrow travel lanes calm traffic; tight curb-return radii slow turning vehicles and shorten pedestrian crossings. For those dimensions the *bottom* of the range is the desired urban outcome, and the thing to guard against is an applicant building them *too wide* "for safety." So the governing principle is not "biggest number wins" but **"the configuration that best realizes the Type's stated intent in its context"** — which means narrower lanes *and* fuller pedestrian infrastructure at the same time.

**(b) The pressure should track the transect.** "Bare minimum" is the *correct* answer for a Rural Road (R2) or Rural Lane (R3): the Comprehensive Plan's own direction is "less road," "right-sized infrastructure," and minimal alteration of the rural landscape (pp. 43–44, 116). We do *not* want to mandate sidewalks, street trees, and 50-ft sections on a D1 farm road. The problem the Board is worried about is overwhelmingly a **Street-family problem** — it lives in D5/D6 and the village districts, where skipping the sidewalk, the street trees, the planting strip, or the on-street parking quietly defeats the public realm the District is supposed to create. Any "require more" mechanism should therefore be **strong in the urban/village Types and light-to-absent in the rural Types.**

It is useful to sort the calibrated items into two kinds, because they need different tools:

| Kind | Examples | Cheap-build default | Tool that fits |
|---|---|---|---|
| **Provision components** (present vs. absent) | sidewalk, planting strip, street trees, on-street parking, curb | *absent* | objective "shall require where…" triggers; presumptive "provided unless…" |
| **Dimensional ranges** (pick a number) | right-of-way width, lane width, parking-lane width, curb-return radius | *the cheap end* (usually min; for lanes/radii, watch for max) | presumptive design value + burden to justify departure |

---

## 3. The legal constraint — guided discretion, not standardless discretion

Maine is a home-rule state, but the Law Court has long required that a land-use ordinance contain **standards sufficient to guide the decision-maker and to permit meaningful review.** A provision that lets a board grant or withhold something on an unguided judgment is vulnerable as an unlawful delegation of legislative power or as void for vagueness. The leading case is *Cope v. Inhabitants of Town of Brunswick*, 464 A.2d 223 (Me. 1983), where the Court struck a standard authorizing denial of a permitted use that would "adversely affect the health, safety or general welfare" because it supplied no ascertainable standards. (The drafter should confirm the current state of this doctrine before adoption; the principle has been stable for decades.)

The practical consequence for us: **a bare "the Planning Board may require additional components as it deems appropriate" clause is the wrong answer.** It would be the most flexible option and the least defensible — an aggrieved applicant or abutter could attack any decision under it. Everything recommended below is built to satisfy the standards doctrine by tying each requirement to **enumerated criteria** and, where discretion is exercised, to a **written-findings requirement.** Newcastle's existing subdivision and site-plan review provisions already operate under this doctrine; the new criteria should be drafted to at least the same level of definiteness.

A second institutional point follows from the same doctrine. Discretion is far safer in the hands of the **Planning Board** — a multi-member body acting after a public hearing and making written findings on the record — than in the hands of the **Code Enforcement Officer**, a single administrator. The draft's §13.c already splits the work this way: the CEO handles driveways, entrances, and maintenance; the Planning Board handles new streets, substantial reconstruction, and reclassification. New streets — the heart of the Board's concern — come to the Planning Board, usually through subdivision review. So the natural home for any *judgment-based* "require more" authority is the Planning Board in subdivision/site-plan review, while the CEO should be given only **bright-line, self-executing** triggers to administer.

---

## 4. The toolbox — five mechanisms

These are not mutually exclusive; the recommendation in §5 combines several.

### Option A — Presumptive (default) design values + burden-shift

Replace the "everything is a minimum" rule with a **presumptive design value** for each range — the value that best serves the Type's intent — and require an applicant to *earn* a departure from it by meeting stated criteria. For most Street-family components the presumptive value is the fuller one (sidewalk provided, planting strip provided, mid-or-upper ROW); for traffic-calming dimensions (lane width, curb radius) the presumptive value is the *lower* one. The `types.json` that drives the Type pages already carries a "typical" value for each right-of-way — that concept can be promoted from "the number we drew the picture at" to "the number you build unless you justify otherwise."

- **Pros:** The single most effective fix; it flips the default so minimum becomes the *exception*. Rule-like and predictable. Largely CEO-administrable.
- **Cons:** Requires setting a presumptive value for every dimensioned row (a one-time drafting task). Slightly less applicant freedom.

### Option B — Objective "shall require" triggers (bright-line rules)

A short, **closed list** of context conditions that *require* a specific component, applied without discretion. Illustrative triggers:

- *Sidewalk* — required both sides in D5/D6; required on at least one side where the segment lies within ¼ mile of a school, the Town Office, a place of public assembly, a public park, or **an existing sidewalk it can connect to** (the connectivity rule); required on the side abutting the more intensive use.
- *On-street parking* — required where the abutting frontage permits ground-floor retail or commercial use, and where it serves the Type's traffic-calming function.
- *Planting strip + street trees* — required where the Type carries a sidewalk (to buffer it from traffic) and where the abutting District has a build-to/streetwall standard.
- *Street connectivity / stub-outs* — required to connect to abutting developable parcels and to any street stubbed to the boundary, to build the network the villages depend on.

- **Pros:** Most defensible and predictable; self-executing; the CEO can apply them; an applicant knows the rules up front.
- **Cons:** Rules cannot anticipate every situation and can be over- or under-inclusive at the margins; needs a discretionary backstop (Option C) for the cases the rules miss.

### Option C — Guided discretion with mandatory written findings

For new streets in subdivision/site-plan review, direct the **Planning Board** to select, from the assigned Type's range and optional components, the configuration **necessary to achieve an enumerated list of design objectives**, and to **state in writing** which objective(s) support each requirement that exceeds the minimum. The objectives are drawn directly from Article 3 §1 Purpose and the cited Comprehensive Plan policies, e.g.:

1. pedestrian safety and comfort consistent with the Type's pedestrian-priority weighting (§2.c.3);
2. continuity of the pedestrian and street network (connection to existing sidewalks, streets, and trails);
3. consistency with the abutting District's intended character and with the Comprehensive Plan;
4. stormwater management and street-tree canopy;
5. emergency-vehicle access and circulation;
6. on-street parking sufficient to serve adjacent uses and to calm traffic;
7. in rural Types, preservation of rural character and minimal alteration of the landscape (this objective *cuts toward the minimum*).

- **Pros:** Flexible and context-sensitive; defensible because the objectives are enumerated and the findings create a reviewable record; this is how good form-based codes handle the cases bright-line rules can't.
- **Cons:** More process; depends on Planning Board and staff capacity; less certainty for applicants than a bright-line rule.

### Option D — Master-Plan / pattern-book pre-commitment

For larger developments, use the Master Plan already contemplated in the renumbered Article 8 §13 to **pre-assign Types and cross-section configurations for all internal streets**, reviewed and fixed by the Planning Board up front. Street standards then flow from the approved Master Plan rather than being litigated lot-by-lot.

- **Pros:** Front-loads the design conversation; excellent for multi-street subdivisions; gives the developer certainty once approved.
- **Cons:** Only reaches developments large enough to require a Master Plan; not a general fix for the one-off new street.

### Option E — Incentive alignment (carrot, not stick)

Reward the fuller cross-section with a by-right benefit — e.g., a modest lot-yield/density bonus, a reduction in required off-street parking where on-street parking and sidewalks are provided, or expedited review — so that good public-realm design pays for itself.

- **Pros:** Sidesteps the discretion problem entirely; rewards rather than compels; politically easier.
- **Cons:** Gives something away; the incentive may be too small to overcome construction cost; works best as a *supplement*, not the primary tool.

---

## 5. Recommended approach — a layered default + trigger + findings structure

No single mechanism does the job well. The recommendation is a **three-layer structure** that matches the right tool to each kind of decision, keeps the CEO's role bright-line, reserves judgment for the Planning Board, and respects the transect:

**Layer 1 — Fix the default (Option A).** Replace §3.c.4's "everything is a minimum" with a **presumptive-value rule**: the design value stated for each Type is the value to be built; an applicant may go below it only on a demonstration, meeting stated criteria, that the safety standards are still met and that the reduced section still serves the Type's purpose. Safety-critical dimensions (traveled-way width, sight distance per Table 3.2, intersection geometry, the 2% near-intersection grade) remain fixed for every Type, exactly as they are today — so this layer never trades away safety.

**Layer 2 — Bright-line triggers the CEO can administer (Option B).** Add a closed list of objective "shall provide / shall require where…" triggers for the provision components (sidewalk, planting strip, street trees, on-street parking, connectivity), weighted to the Street family and the village/town-center Districts and explicitly light in the rural Types. Because these are self-executing, they can apply to *any* new-street permit, including those the CEO handles, and they give applicants certainty.

**Layer 3 — Guided Planning-Board discretion with findings (Option C).** For new streets in subdivision/site-plan review, give the Planning Board authority to require, *from within the assigned Type's range and optional components*, whatever the enumerated design objectives warrant beyond the Layer-2 floor — with a **mandatory written finding** identifying the objective(s) that justify each such requirement. This is the flexible backstop, and the findings requirement is what makes it defensible.

**Keep two things out of it:** (1) do not give the *CEO* open-ended "require more" power — that is the legally exposed move; the CEO gets Layers 1–2 only. (2) Do not push the rural Types up — the rural objective in Layer 3 cuts toward the minimum, consistent with "less road."

Optionally layer in **Option E incentives** as a sweetener and reserve **Option D (Master Plan)** for large subdivisions.

This structure also reads cleanly against the draft's existing voice: it generalizes the "may require where [the Authority] determines [X] is necessary" grammar already used in §7.d.3 (driveway culverts) and §14.d.1.b–c (dead-end easements), and it routes judgment to the body §13.c already designates for new streets.

---

## 6. Illustrative draft language (NOT proposed for adoption)

Offered only to make the options concrete. Numbering is provisional.

**Revised §3.c.4 (presumptive value — replaces "all measurements are minimums"):**
> *"The design value stated for each Type is the value to be provided. Where a range is stated, the upper-bound pedestrian and landscape components (sidewalk, planting strip, street trees, on-street parking) are presumed to be provided in the Street family (S1–S5), and the lower-bound traffic-calming dimensions (travel-lane width, curb-return radius) are presumed in all Types. An applicant may depart from a presumed value only upon a demonstration, submitted with the application, that (i) every safety-critical standard of this Article is still met, and (ii) the departure better serves the purpose of the assigned Type in its District context. The safety-critical standards — traveled-way width, sight distance (Table 3.2), intersection geometry (Section 9), and the maximum grade within 75 ft of an intersection — are fixed for every Type and are not subject to this subsection."*

**New §3.f — REQUIRED COMPONENTS BY CONTEXT (Layer 2 bright-line triggers):**
> *"In addition to the components stated for the assigned Type, the following components shall be provided where the stated condition exists, regardless of the minimum stated for the Type:*
> *1. A sidewalk shall be provided on both sides in D5 and D6, and on at least one side of any Street segment that (a) lies within ¼ mile of a school, the Town Office, a place of public assembly, or a public park, or (b) can connect to an existing sidewalk on an abutting segment.*
> *2. On-street parking shall be provided where the abutting frontage permits a ground-floor retail or commercial use.*
> *3. A planting strip and street trees shall be provided on any Street segment carrying a required sidewalk, except where the Code Enforcement Officer finds that subsurface utilities or existing mature trees make planting infeasible.*
> *4. A new street shall connect to any street stubbed to the boundary of the parcel and shall stub to abutting developable parcels to provide for future connection.*
> *These requirements do not apply to the Road family (R1–R5) except where a Road segment directly abuts a D5 or D6 frontage."*

**New §6.d.x — PLANNING-BOARD SELECTION OF COMPONENTS (Layer 3 guided discretion + findings):**
> *"In approving a new street or road under this Section, the Planning Board may require, from within the range and optional components of the assigned Type, components or widths exceeding the minimum where necessary to achieve one or more of the following objectives: (1) pedestrian safety and comfort consistent with the Type's pedestrian-priority weighting under §2.c.3; (2) continuity of the sidewalk and street network; (3) consistency with the abutting District's intended character and with the Comprehensive Plan; (4) stormwater management and street-tree canopy; (5) emergency-vehicle access; (6) on-street parking adequate to serve adjacent uses and to calm traffic. For each component or width it requires under this subsection, the Planning Board shall state in writing the objective(s) that support the requirement. In the Road family (R1–R3), the Board shall also weigh the preservation of rural character and the minimization of land alteration, which may warrant the minimum section."*

**Per-Type-page annotation.** Each Type page in §2 could carry a small "presumptive value" marker on the dimensioned rows and a footnote keying the soft components ("optional," "encouraged") to §3.f / §6.d, so the reader sees the trigger at the point of use. This is a `types.json` + plate-renderer change, deferred until the policy is settled.

---

## 7. Where this would attach in the draft (drafting hooks, for later)

- **§3.c.4** — replace the "minimums" rule with the presumptive-value rule (Layer 1).
- **New §3.f** — bright-line required-components-by-context list (Layer 2).
- **§6.c–§6.d** — Planning-Board selection authority + findings requirement for new streets (Layer 3); §6.c already routes Type assignment through the CEO/Road Commissioner/Planning Board.
- **§13.c** — confirm the CEO gets Layers 1–2 only; Planning Board gets Layer 3.
- **§2 Type pages / `types.json` / `cross-section-plates.typ`** — optional presumptive-value markers and trigger footnotes.
- **Article 9 definitions** — possibly add "presumptive value," "provision component," and a cross-reference for "required component."
- **Article 8 §13 Master Plan** — optional pre-commitment pathway (Option D).

None of these are touched until the Board picks an approach.

---

## 8. Tradeoffs and risks to weigh

- **Cost vs. placemaking.** Every required component raises the cost of a new street. In the village/town-center Districts that cost buys the public realm the District exists to create; in the rural Districts it would buy nothing the Plan wants. The transect-weighting in the recommendation is what keeps the cost where it earns its keep.
- **Predictability vs. flexibility.** Bright-line triggers (Layer 2) give applicants certainty; findings-based discretion (Layer 3) gives the Town adaptability. The layered structure deliberately buys most of the certainty up front and reserves discretion for the residual cases.
- **Legal exposure.** Concentrated in Layer 3; managed by the enumerated objectives + mandatory findings, and by keeping open-ended discretion away from the CEO.
- **Administrative capacity.** Layer 3 asks the Planning Board to make and document findings. That is ordinary subdivision-review work, but it is real work; the bright-line layers exist partly to keep the routine cases off the Board's plate.
- **Interaction with the ROW memo.** The companion ROW memo lowered the right-of-way *floors* so the ranges are not over-wide. The presumptive-value rule here ensures the lowered floor does not silently become the universal build. The two memos are complementary: one set sane outer bounds; this one sets the default *within* them.

---

## 9. Decisions for discussion — with drafter's recommendation

Each decision is stated as a question for the Board, followed by the drafter's recommended answer. The recommendations are internally consistent — they assume the layered structure of §5 — but each can be adjusted independently.

**1. Adopt the layered structure (Layers 1–3), or a subset?** Is the Board comfortable with Layer 3 (guided Planning-Board discretion + findings), or does it prefer bright-line triggers alone (Layers 1–2) for maximum predictability?

> **Recommendation: adopt all three layers, with Layer 3 tightly bounded.** Each layer does work the others cannot, and dropping any one re-opens the problem: without Layer 1 the "minimum by right" ratchet remains and the other layers fight uphill against it; without Layer 2 every routine sidewalk becomes an argument; without Layer 3 the bright-line rules are left to anticipate every case, and the cases they miss fall to the minimum. Layer 3 is made safe not by trimming it but by bounding it: the Planning Board may require components only *from within the assigned Type's range and optional list* — never beyond the Type — and only against the enumerated objectives, on written findings. Requiring a fuller section than the Type allows is not a Layer-3 act; it is a **reclassification to a higher Type**, which §13.c already routes to the Board on findings.

**2. Confirm the transect-weighting.** Is the pressure rightly strong in the Street family and the village Districts and absent in the rural Types — and where exactly does the line fall for D2 and the Special Districts?

> **Recommendation: confirm it, scaled by Type rather than on/off, per the table below.**
>
> | District | Side of the line | Strength of the presumption |
> |---|---|---|
> | D6 Town Center; D5 Village Business; SD-Historic core | Village | **Full** — both-side sidewalk, planting, trees, on-street parking (S1/S2) |
> | D3 Neighborhood Business; D4 Village Residential; SD-Civic; SD-Campus | Village | **Moderate** — one-side sidewalk + planting + trees presumed (S3/S4) |
> | D2 Neighborhood Residential | Village edge | **Moderate, one-sided** — sidewalk one side presumed |
> | SD-Highway Commercial (R4) | Special | **Feasibility-gated** — sidewalk/planting "where feasible"; Town governs frontage, MaineDOT the cartway |
> | D1 Rural; SD-Conservation; rural SD-Marine; SD-Rural Highway (R5) | Rural | **Off** — the minimum is the correct answer ("less road") |
> | SD-Fabrication | Freight-first | **Light** — internal S5 Alleys; freight & emergency access govern |
>
> The contestable line is **D2**: the recommendation places it on the village side (sidewalk one side presumed), because a missing D2 sidewalk is both keenly felt and expensive to retrofit. The relief valve for genuinely small D2 infill is the dwelling-unit trigger in Decision 4, not a softening of D2 as a whole.

**3. Set the presumptive values** — for each dimensioned row, is the presumptive value the mid-range typical, the upper bound, or (for lanes and radii) the lower bound?

> **Recommendation: adopt one governing rule, then the specific flips below.** The governing rule: the presumptive value is *the configuration that best realizes the Type's intent in its District* — which means fuller pedestrian and landscape components together with **narrower** traffic dimensions. Concretely: right-of-way presumes the **typical (mid-range)** value for Street Types and the **minimum** for the rural Road Types (R1–R3: less land alteration per the Plan); travel-lane width and curb-return radius presume the **lower** end in all Types (bounded by the fixed safety floor); the provision components presume **provided**, scaled by Type. The rows that change from the current draft:
>
> | Type | Row | Current draft | Presumptive value |
> |---|---|---|---|
> | S2 | Planting strip | "optional, both sides" | **provided, both sides** |
> | S3 | Street trees | "encouraged" | **provided** where a sidewalk or planting strip is built |
> | S3 | On-street parking | "permitted, one side" | **provided one side** in D3 and where lots front |
> | S4 | Street trees | "encouraged" | **provided** where a planting strip is built |
> | S1–S4 | Travel-lane width | range (e.g. S1 10–11 ft) | **lower end** (S1: 10 ft) |
> | S1–S5 | Curb-return radius | range | **lower end** |
> | R1 | Sidewalk | "optional" | stays optional, **but** the Layer-2 connectivity trigger forces it where R1 abuts a D2 frontage or connects an existing village sidewalk |
>
> Everything else already sits at its sensible default. Left as-is (not presumptive levers): design speed, maximum grade, maximum block length (a cap, not a floor), sight distance, pavement, and surface — these are fixed safety values or maxima. On-street parking on S4/S5 stays genuinely optional; they are service ways.

**4. Fix the Layer-2 trigger thresholds.** Are the ¼-mile sidewalk catchment, the "ground-floor retail" parking trigger, and the connectivity/stub-out rule the right bright lines — and are there others?

> **Recommendation: keep three, add two, defer one.** Keep the **¼-mile sidewalk catchment** (the standard five-minute-walk radius), but anchor it to *named* Newcastle destinations — the village schools, Town Office, library, post office, public landings and parks, and places of public assembly — so it is an objective lookup. Keep the **connectivity rule** and treat it as the most important trigger (sidewalk where it can join an existing sidewalk; new street connects to any street stubbed to the parcel and stubs to abutting developable parcels). Keep the **on-street-parking trigger** but tie it to the use table ("where the abutting District permits ground-floor retail, restaurant, or personal-service use"). **Add** a **trail trigger** (path tie-in where a segment abuts or crosses a mapped trail or the planned village trail network) and a **dwelling-unit trigger** (a new street serving more than roughly 10–15 dwelling units gets a sidewalk on at least one side regardless of District — this both catches the larger D2/D4 subdivision and is the relief valve that lets small D2 infill stay light). **Defer** a transit trigger — Newcastle has no fixed-route transit to anchor it; note it as a future hook. Hold the list at about five so it stays self-executing.

**5. Pursue incentives (Option E) and/or Master-Plan pre-commitment (Option D)?**

> **Recommendation: adopt both, in different weights.** Adopt **Master-Plan pre-commitment** as a real pathway — it is nearly free because the renumbered Article 8 §13 already contemplates a Master Plan; add a sentence fixing the Types and cross-sections for all internal streets at Master-Plan approval, with the approved sections governing thereafter. It front-loads the hardest design conversations for large subdivisions and gives the developer certainty. Adopt one **narrow incentive**: count the on-street parking the applicant builds toward the development's required off-street parking, so the fuller section pays for itself by shrinking the off-street lot — no giveaway of density and no new discretion. Defer density and lot-yield bonuses to a later phase; their policy footprint is larger.

**6. Who bears the discretion?** Confirm that the CEO administers only bright-line items and the Planning Board exercises the judgment-based authority, consistent with §13.c.

> **Recommendation: confirm the §13.c split, with two clarifications.** The CEO administers **Layers 1–2** (presumptive values and objective triggers) on the permits the CEO already handles — driveways, entrances, single-lot frontage work; the **Planning Board** exercises **Layer 3** (guided discretion + findings) on new streets and substantial reconstruction, which already reach the Board through subdivision and site-plan review. *Clarification A:* where a Layer-2 trigger carries a narrow judgment ("planting infeasible due to utilities," R4 "sidewalk where feasible"), that call is the CEO's on CEO-permits and the Board's where the matter is already before the Board — but either way it requires a one-line written reason, so even the bright-line layer leaves a record. *Clarification B:* neither body may require a section *beyond* the assigned Type's range; the only route to a fuller section than the Type allows is reclassification to a higher Type, a Planning Board action on findings.

---

**Net effect of the recommendations.** The default new street in a village District arrives with its sidewalk, planting strip, street trees, and on-street parking already in the section; an applicant may still build leaner, but must *earn* the reduction on a stated demonstration rather than receive it by right. A D1 farm road still defaults, correctly, to a minimal section. On the Board's direction, the chosen answers can be written into Article 3 (the hooks in §7), reflected on the Type pages, and carried into the next release with a regenerated redline and Summary of Changes.
