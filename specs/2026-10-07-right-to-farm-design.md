# Right to Farm — design specification

**Town of Newcastle, Maine · Core Zoning Code · branch `right-to-farm`**
Written 2026-10-07 against the Code adopted at the Special Town Meeting of September 14, 2026
(CZC v1.0, nine articles). Decisions in §2 were made by the Planning Board chair in brainstorming
on 2026-10-06 and 2026-10-07. The homework behind §§3–7 is the twelve-agent review recorded at
`scratchpad/rtf/homework.md` (167 findings, 9 blocking); the Code scan is `scratchpad/rtf/current-state.md`
and the first law pass is `scratchpad/rtf/maine-law.md`.

> **Citation caution.** Every statute cited here was opened during the research, but two earlier
> passes produced citation errors that had to be corrected, and 21 items remain marked UNVERIFIED in
> the homework's source list. Town counsel cite-checks before any of this reaches a warrant article.

---

## 1. What this is for

In the chair's words: farming should run as a spectrum, from a vegetable garden in any neighborhood
district up to full-scale commercial farming in D1. D1 is not the only place for farming or for the
buildings that support it. Allow it in almost all districts, with degrees of size, scale and impact,
and separation distances that respond to how close the district is to downtown. Bias toward the
permissive end. Belt and suspenders: use-and-district permission plus operative protection.

**The finding that shaped the design.** The Code today is *more* permissive than our first draft of
it. Article 7 §1 already provides that "Private, non-commercial agricultural uses are permitted in
every district", and Article 9 brings Large Animals — "cows, sheep, pigs, and horses raised for home
use or for profit" — inside Agricultural Use, with no cap and no separation standard. A tier ladder
imposed over that would have withdrawn medium and large stock from seven or eight districts and
capped birds at six everywhere. This spec therefore adds structure **without subtracting existing
rights**: see the savings clause at §3.8.

## 2. Decisions

| # | Decision | Made |
|---|---|---|
| D1 | Home/Personal Agriculture requires **no permit**; general standards of the Code still apply | 2026-10-07 |
| D2 | **Existing non-commercial agriculture is preserved** by an express savings clause | 2026-10-07 |
| D3 | **D1 farm buildings stay uncapped**; Board-review thresholds start at D2 | 2026-10-07 |
| D4 | Tier separation distances keep the tier table, **gated on lot width**, and apply as the **greater of** the table and the district's accessory setback | 2026-10-07 |
| D5 | The scheme lives in a **new Article 7 §3, "Right to Farm"**, accepting the 63-section renumbering and the tooling work it requires | 2026-10-07 |
| D6 | **Agriculture** becomes an umbrella over **Home/Personal Agriculture** and **Commercial Agriculture**, regulated separately by scale and impact | 2026-10-07 |
| D7 | **Selling**: produce grown or made on the lot, sold from the lot, stays Home/Personal — including a farm stand. Selling others' products, or producing for wholesale, is Commercial | 2026-10-07 |

Rejected, with reasons: distributing the scheme across the existing use sections (reproduces the
scattered-nonconformity pathology the other branch exists to cure); a new Article (renumbers Articles
8 and 9 a year after the last renumbering, rippling into the adopted baseline, the redline machinery
and the permit app's citation layer); renaming §16 in place (keeps section numbers stable but buries
a town-wide right inside an alphabetical use entry).

## 3. The scheme

### 3.1 Definitions (Article 9)

**Agriculture** — the cultivation of plants and the keeping of animals, comprising **Home/Personal
Agriculture** and **Commercial Agriculture**, which this Code regulates separately because they
differ in scale and impact.

**Home/Personal Agriculture** — agriculture that is not Commercial Agriculture. Includes cultivation
of food-producing plants and flowers, keeping of bees, and keeping of animals within the tiers of
§3.3, together with the sale from the lot of products grown or made on that lot.

**Commercial Agriculture** — agriculture carried on for the commercial production of agricultural
products, including production for wholesale and the sale of products not grown or made on the lot.
Drafted to track 7 M.R.S. §152(5)–(6) so that the class the state shield protects and the class this
Code calls commercial are the same class.

Also defined, because nothing in Article 9 defines them today: farm stand · greenhouse · hoop house ·
high tunnel · manure storage · best management practices · agritourism · on-farm processing · small
stock · medium stock · large stock · agricultural building. Reconciled: the existing **Agricultural
Use** definition (which sweeps in equine activity and Large Animals for home use) folds into
Home/Personal Agriculture with numbers attached; **Agricultural Building** is defined twice in
Article 9 and one of the two excludes hoop houses — resolve to a single definition.

One drafting rule throughout: the Code currently uses five variant trigger phrases — *agricultural
activities*, *agricultural uses*, *commercial agricultural uses*, *active agricultural use*, *new
Commercial Agricultural uses*. All five resolve to the two defined terms above.

### 3.2 Permission model

**Home/Personal Agriculture requires no permit.** This is both a policy choice and a legal necessity:
7 M.R.S. §293 gives a right to cultivate vegetable gardens "notwithstanding any provision of law to
the contrary", and §296 preserves only ordinances "of a general nature that does not solely or
specifically apply to vegetable gardens". A Use Permit aimed at a cultivation tier is aimed
specifically at gardens.

This requires something the Code does not currently have. Article 1 §2.b.8 provides that
"Acquisition of a permit is mandatory prior to enacting anything noted as 'Permitted' in this Code",
and the use-table data model carries exactly four status codes, with the legend stating that uses
without one of them "are not allowed in this District". So the spec must add **a fifth status —
permitted without a permit** — to the legend, the district tables and the Article 2 rendering, and
§3 must expressly displace Article 1 §2.b.8 for Home/Personal Agriculture. Moving between tiers is
expressly not a change of use under Article 7 §1.g.

**Commercial Agriculture keeps a permit**, and reaches the Planning Board only through §3.4.

What §296 *does* preserve is general standards — setbacks among them. So Home/Personal Agriculture
being permit-free does not mean standard-free; the separation distances of §3.5 apply to it.

### 3.3 Tiers and districts

| Tier | What it covers | Where |
|---|---|---|
| Cultivation | Growing anything at any scale, and sale from the lot of what is grown there | All thirteen districts |
| Bees | Hives, subject to state registration | All thirteen districts |
| Small stock | Six birds (hens or ducks; no roosters or drakes) plus up to six rabbits | All thirteen districts |
| Medium stock | Goats, sheep, miniature breeds | D1, D2, D3, SD-Rural Highway, SD-Conservation, SD-Campus |
| Large stock | Cattle, horses, pigs, llamas, emus and heavier | D1, D2, SD-Rural Highway, SD-Conservation, SD-Campus |

Special districts: SD-Rural Highway and SD-Conservation as D1; SD-Campus as D2; SD-Historic,
SD-Fabrication, SD-Marine and SD-Highway Commercial as D5.

Small stock reaches all thirteen districts because a 2025 statute reported at 7 M.R.S. §219-D bars a
municipality from banning residential chickens. **Counsel confirms before drafting** (Q1).

**The tiers are a floor, not a ceiling, for what already exists** — see §3.8. And the tiers need two
additions the first draft lacked: a rule for flocks larger than six, and a home for poultry other
than hens and ducks (turkeys, geese).

### 3.4 What reaches the Planning Board

Everything agricultural is by right except these six. Thresholds are starting numbers for the Board.

| Trigger | Threshold |
|---|---|
| Slaughter for sale | Any, as a commercial service. Killing for the household stays by right |
| Processing for wholesale | Any processing for distribution off the farm. Washing, sorting, drying, packing and processing sold direct from the farm stay by right |
| Importing off-site organics | More than 50 cubic yards per year. Composting the farm's own waste and bedding stays by right at any volume |
| Agritourism events | More than 50 attendees, or more than 12 events a year |
| Farm buildings | **D1 uncapped** (decision D3). Over 5,000 sq ft in D2; 3,000 in D3; 2,000 in D4, D5 and the districts mapped to them |
| Manure storage | Over 50 cubic yards **and** within 100 ft of a property line, or within 300 ft of a well or water body |

Two corrections from the homework are already applied above. The manure trigger was drafted with
"or", which caught every backyard compost pile within 100 ft of a line — it is now conjunctive for
the volume test. And **D1 is uncapped**: D1 is the only district whose Permitted Buildings matrix
already carries an "Agricultural Use" column, CEO-permitted with every dimension uncapped, so a
threshold there would have *added* Board review to the farming district.

The claim that nothing else reaches the Board is not yet true: residual Board routes exist elsewhere
in the Code (S1), including the five district-page sentences allowing the CEO to refer a project to
the Planning Board, and Article 8 §10.e / §11. §3 must state which of these it displaces.

### 3.5 Separation distances

| Tier | From a property line | From a dwelling on another lot | By right where lot width is |
|---|---|---|---|
| Cultivation | None beyond district standards | None | Any |
| Bees | 10 ft, or a flyway barrier at the line | None | Any |
| Small stock housing | 10 ft, or the district accessory setback if greater | 25 ft, on lots ≥ 50 ft wide | Any |
| Medium stock housing | 50 ft | 100 ft | ≥ 120 ft |
| Large stock housing | 100 ft | 150 ft | ≥ 220 ft |
| Manure storage | 100 ft | 300 ft from a well or water body | — |

Three rules make the table work:

1. **Greater-of.** The distance is the greater of this table and the district's Accessory Building
   Placement setback. D3 (12 ft), D5 (15 ft) and SD-Rural Highway (15 ft) are already stricter than
   the table's 10 ft, and the table must not silently loosen them.
2. **Lot-width gate, for medium and large stock only.** Those tiers are by right where the lot can
   hold their distances; below the gate they are not prohibited but require Planning Board approval
   of a reduced separation, with criteria. Without this the table is an empty permission: large
   stock needs 220 ft of width and **D2's maximum lot width is 200 ft**; at minimum widths, medium
   and large stock fail even in D1, whose minimum width is 100 ft, not the 250 ft Primary Frontage
   Line Length figure.
   **Small stock takes no gate.** A width test would push six hens on a narrow D5 or D6 lot to the
   Planning Board, which decision D1 forbids and 7 M.R.S. §219-D may preempt outright. On a lot too
   narrow for 10 ft, the district accessory setback governs; the 25 ft dwelling separation applies
   only where the lot is at least 50 ft wide.
3. **Measuring convention.** Distances to a dwelling are measured as Article 7 §3.b.1.a already
   measures them — to the nearest boundary of the lot containing a residence, not to the dwelling
   itself — so a neighbour's later addition cannot retroactively put a farm out of compliance.

Open: whether pens, runs, paddocks and pasture hold any separation, or only housing and manure
storage (Q14). Front setbacks are not addressed by the table and must be, since they run from 10 ft
in D1 to 50 ft in SD-Highway Commercial.

### 3.6 Buildings

- **An agricultural building type** in Article 5, with greenhouses as a variant: barn, greenhouse,
  equipment shed. The Permitted Buildings matrices in every district where farm buildings are
  allowed gain an Agricultural Building column with its own width, depth, floor area, stories,
  heights and permitting authority — because today the accessory envelope caps at 30 × 40 ft
  (1,200 sq ft) in every non-D1 district, which sits *below* the thresholds in §3.4 and would make
  them dead letters. D1's existing "Agricultural Use" column is renamed to match the type.
- **Three districts have no Permitted Buildings matrix at all** — SD-Conservation, SD-Campus and
  SD-Marine carry `"matrix": null`, and Article 5 §3 applies only in a district that has one. The
  spec must say what farm buildings may do there. **D6 has no Residential Accessory column** and
  every D6 permitting-authority cell reads Planning Board.
- **Article 5 §18 already carries a "Connected Farm" building group**, permitted in D1–D4 and
  SD-Historic, contemplating a barn and house on one lot. The new type is drafted to sit alongside
  it, not to contradict it. The word "barn" is used operatively six times in the Code and defined
  nowhere.
- **Unenclosed and seasonal structures are not buildings** and take no type: hoop houses, high
  tunnels, trellising, fencing, temporary animal shelters, field-season equipment covers. Exempt
  from the Article 5 additional-structure cap and from the three-month temporary-structure removal
  rule, which currently makes an overwintering tunnel illegal.

### 3.7 Protection

Three provisions, each doing a different job.

1. **Declaration.** Agriculture is expected and encouraged in every district where it is permitted,
   and the presence of a lawful agricultural operation is not itself grounds for restricting
   ordinary agricultural activity.
2. **The state shield, described accurately.** 7 M.R.S. §154 provides that a farm operation in "an
   area where agricultural activities are permitted" may not be considered a violation of a
   municipal ordinance if it conforms to best management practices as determined by the
   Commissioner. Three things follow that the first draft had wrong:
   - It **switches on town-wide by force of state law** the moment agriculture is permitted. The
     Code cannot scope it to a list of standards. Concretely: Article 4 prohibits barbed wire
     outright, and a BMP-conforming cattle operation fencing with barbed wire is shielded. **This
     trade — permission buys the shield — is the single largest consequence of the amendment and
     belongs in the Summary of Changes in plain words.**
   - It reaches **commercial** operations only. 7 M.R.S. §152(5) defines "Farm" by commercial
     production, and §152(2) excludes trees grown for forest products. Household gardens, six hens
     and hobby rabbits are outside it; bees and compost are inside it.
   - Conformance is **the Commissioner's determination under §156**, not the CEO's. The Code must not
     purport to have the CEO decide it.
3. **The Code's own safe harbour, for what the statute does not reach.** An activity meeting the
   numeric standards of §3 is not a violation of the Nuisance Standards at Article 7 §1.h. This is
   objective, a CEO can apply it with a tape measure, and home rule permits the Town to go broader
   than the statute (30-A M.R.S. §3001) though never narrower.

**Burden.** Article 1 §2.d.1 puts the burden on the applicant. The spec preserves it rather than
displacing it: the operator claiming the shield bears the burden of showing BMP conformance, with
the §156 finding as the natural showing. Drafted as a rule of decision keyed to Article 7 §1.h,
Article 8 §18.e and Article 4 §12.h — not to the bare word "nuisance", which no Article 9 entry
defines and which Article 1 §2.b.2 would therefore send to Webster's. Note 30-A M.R.S. §4302 already
makes a use existing in violation of a land-use ordinance a nuisance by statute, so the operative
provision is the shield, not a declaration.

### 3.8 Savings clause for existing agriculture

Inside §3, not in the nonconformity provisions:

> An agricultural activity lawfully conducted on the effective date of this Section may continue at
> its then-existing scale and location, without a permit and without becoming a nonconforming use;
> such an operation may enter a tier voluntarily; and nothing in this Section requires any existing
> building, fence, structure or manure facility to be altered.

This is necessary because Article 8 §25 would not catch these operations: it is keyed three times to
conditions existing "prior to the adoption of this Code" and never to an amendment. (Article 9's two
nonconformity definitions disagree with each other on exactly this point — flagged for the
`nonconformity` branch, not fixed here.)

### 3.9 Re-keying the six existing carve-outs

Six provisions today turn on whether a **lot** is "used for agricultural activities": the fence
material and crossing exemptions (Article 4 §8), the field-review exemption (Article 4 §7), the
one-accessory-building cap and the no-primary-building allowance (Article 5 §9), and the outdoor
storage and work-yard screening exemptions (Article 5 §18). Once Cultivation is permitted in all
thirteen districts, any lot in town can qualify with a token planting, and the carve-outs transfer to
whatever non-farm use shares the lot — a landscaping yard, a contractor's equipment, a kennel.

All six are re-keyed to the **activity and its own footprint** rather than the lot, using Article 1
§2.c.6 ("'lot' … also refer[s] to any portion thereof"), with a threshold so a token planting does
not qualify. The spec states expressly that a co-located non-agricultural business gets no benefit
from any of them.

## 4. Consequential edits

- **Article 1** — §2.b.8 displaced for Home/Personal Agriculture; the five variant trigger phrases
  resolved to the two defined terms.
- **Article 2** — the thirteen district use tables gain the agriculture rows and the new permit-free
  status; the Permitted Buildings matrices gain the Agricultural Building column; D1's existing
  column renamed. Note the data hazard: **D4's use column is split mid-word** by a soft hyphen
  (`TRANSPORTATION & UTIL\xad` with zero entries, then `ITIES`), giving D4 eight category blocks
  where the other twelve have seven. Any index-based insert script breaks on it.
- **Article 4** — express agricultural exemptions in fences, lighting, screening and parking. The
  lighting problem has an existing vehicle: §12.c.10 already allows relief for "sites with special
  requirements".
- **Article 5** — the agricultural building type and greenhouse variant; seasonal and unenclosed
  structures exempted; reconciliation with the Connected Farm group in §18.
- **Article 7** — new §3 "Right to Farm"; §16 Commercial Agriculture retained and reconciled; §25
  Farm/Vendor Market and §26 Farmstand permitted (§26 is currently permitted in no district at all);
  §62 Stables reconciled against large stock; §46 Outdoor Storage carved for farm equipment in use.
- **Article 9** — the definitions in §3.1.
- **Housekeeping** — fifteen use sections cite "§1.G" for the Nuisance Standards; the section is
  §1.H.

## 5. Build and tooling work

This is the cost of D5, and it is the reason D5 was taken deliberately.

1. **Section-renumbering suppression.** Inserting §3 renumbers 63 sections. `normalize_for_diff.py`
   today suppresses article renumbering and table renumbering; it has no section-renumbering rule,
   so the next redline would show 63 renumbered headings as unexplained noise in a warrant packet.
   Extend it, with tests. This is reusable by every future amendment that inserts a section.
2. **Permit-review app.** `CONTRACT.md` states "Section numbers are preserved; only article numbers
   shift"; `crosswalk.py` anchors on section identity; a golden string pins "Article 7, Section
   34.b"; a test pins RESIDENCE to its section. All need updating, and the ruleset rebuilt.
3. **Use-matrix builder.** It hard-fails on an added use row and on an unknown status code, so the
   permit-free status must be added to the legend parser and `build_use_matrix.py` before the
   district data changes. (The builder's multi-status support, added for D-0033, is the model.)
4. **Use Table Changes artifact.** The amendment should ship one, so the reader can see what moved
   in thirteen tables without diffing JSON.
5. **Standalones.** Standing rule 4 ships both the integrated Code and the standalone Article; decide
   which standalones this release carries.

## 6. Process and clocks

Three statutory clocks run against the Town Meeting date, and they are not the same clock:

- **7 M.R.S. §155** — the clerk submits the proposed ordinance to DACF **at least 90 days** before the
  Town Meeting that votes on it. This is the long pole.
- **30-A M.R.S. §4352(9)** — the Code's own notice sequence, 13/12/7 days.
- **30-A M.R.S. §3003(2)** — 30 days.

Version: drafts in this cycle are **v1.1-draft** and successors, redlined against the **v1.0**
baseline that was rolled over on September 14, 2026. The adoption version, if this reaches a vote,
is a whole number — **v2.0** — because the version number is the state.

## 7. Open questions

**For town counsel.** Does a permit requirement aimed at cultivation survive 7 M.R.S. §§293, 295 and
296? Does §154 reach a farm building's size or setback? Do Article 8 §18.e criteria survive *Cope*
and *Kosalka* as the governing standards for agricultural special permits? Are special-permit
conditions enforceable against an operation showing BMP conformance? Does 30-A §4352(10) apply to a
town-wide text amendment? Was v1.0 itself submitted to DACF under §155 — and if not, is that a latent
defect worth curing now? Is the Code already prohibiting registered medical-cannabis caregivers
contrary to state law? Should the Code name a DACF publication, or key only to the statutory phrase?

**For the Board.** Do pens, runs, paddocks and pasture hold separation, or only housing? Does the
Code reference §1.h Nuisance Standards for every tier, or only commercial? Is seasonal farm-worker
housing in scope — the Comprehensive Plan carries it as a named action? How does a farm show BMP
conformance, and who may rebut? Which standalones ship? And the rule for flocks over six and for
turkeys and geese, which the tiers do not yet cover.

## 8. Out of scope

Shoreland zoning (separate ordinance; its mandatory manure and tillage setbacks at DEP ch. 1000
§15(N) remain the floor wherever the two overlap). The nonconformity provisions, which are the
subject of a separate branch — except that §3.8 does its own saving, and the Article 8 §25 /
Article 9 disagreement is flagged for that branch. Aquaculture beyond noting that Article 7 §8
governs it.

## 9. Sources

7 M.R.S. §§151–164 (Maine Agriculture Protection Act), §§152, 153, 154, 155, 156, 158 ·
7 M.R.S. ch. 8-G §§291–296 (right to food; vegetable gardens) · 7 M.R.S. §219-D (residential
chickens, reported, UNVERIFIED) · 30-A M.R.S. §§3001, 3003(2), 4302, 4352(9)–(10), 4353(4-C) ·
PL 2025 c.46 (livestock and crop buildings; state building code only) · DEP ch. 1000 §15(N) ·
*Dubois Livestock v. Arundel*, 2014 ME 122 (not opened; for counsel) · Newcastle CZC v1.0, Articles
1, 2, 4, 5, 7, 8, 9 and `source/article-02-data.json`.

Full evidence, with file and line numbers for every Code citation and URLs for every statute, is in
`scratchpad/rtf/homework.md` — including 25 claims examined and cleared, so they are not
re-litigated, and 21 items still marked UNVERIFIED.
