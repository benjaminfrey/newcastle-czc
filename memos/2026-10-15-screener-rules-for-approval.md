# Screener rules: approval record (adopted-v1.0)

Each entry shows what applicants read, the Code section it rests on (quoted from the adopted ruleset), any ruling, and its approval. Production refuses the screener while any entry is a draft.

**Every entry is approved.** A new or changed entry goes back to draft until the chair approves it.

To approve a draft, change `status: draft` to

```yaml
status: approved
approved_by: <name>
approved_on: 2026-10-28
```

## The chair's rulings (2026-10-18)

1. **An owner's own home.** Any home, whether the owner lives in it or rents it out, is the Residence use, so the use table's Residence column decides. Building or placing new homes also runs Residence through the use table.
2. **Residential Companion time limit.** §17.c.1 sends the procedure to §15.D, so §15.d.1's 30 days are shown.
3. **Dividing into fewer than three lots.** The screener asks whether the land was divided in the last five years. No earlier division: not a subdivision under §12.b.1. An earlier division: 'you may need' a Subdivision and the Code Enforcement Officer confirms how the lots count. Unknown: the cautious wording.
4. **Large additions.** Additions over 10,000 sf of floor area are a Large Project Plan. §11.b does not list additions, so this rests on §11.b.1 and the ruling (open item: add additions to §11.b).
5. **Renovations.** The 10,000 sf line measures the whole building's floor area.
6. **MaineDOT entrance permits.** The note applies to any State-owned road, S1 State routes included (open item: §8.c.1's '(R4 or R5)').
7. **Subdivision by homes.** Homes added on the lot within five years count together toward §12.b.3's three (open item for counsel: confirm 30-A M.R.S. §4401(4)).
8. **Who reviews a Large Project Plan.** The Code Enforcement Officer, who may send it to the Planning Board for a public hearing (§11.c.3; §10.c.3 for the Small Project Plan); the Board's 30 + 30 days are shown 'if sent to the Planning Board'.
9. **Use-table codes.** Confirmed: `u` → use permit, `rc` → residential companion, `ex` → expanded use, `sp` → special permit; the D3 `rc sp` cell needs both; a blank cell means the Code doesn't list the use in that district.

Entries that rest on a ruling say so below.

## Applications (`applications.yaml`)

### `use_permit` — Use Permit

- Applicants read: Permission to start a new use of land or a building, or to change from one use to another.
- Reviewer: Code Enforcement Officer
- Time limits shown: 30 calendar days
- Apply on this site: yes
- Applicants read, for `use_permit_decision`: “The Code Enforcement Officer decides within 30 days of accepting your project.” — approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §15.b.1:

  > Applies to all applications seeking to engage in a new Use or a change of Use on a parcel of land, in a building, or group of buildings.

### `residential_companion` — Residential Companion Use Permit

- Applicants read: Permission for a use that goes along with a home on the same lot.
- Reviewer: Code Enforcement Officer
- Time limits shown: 30 calendar days
- Apply on this site: no (Town Office)
- Applicants read, for `use_permit_decision`: “The Code Enforcement Officer decides within 30 days of accepting your project.” — approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Ruling (Ben Frey, Planning Board chair, 2026-10-18): §17.c.1 sends the Residential Companion procedure to §15.D, so §15.d.1's 30 days apply.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §17.b.1:

  > Applies to all applications seeking to engage in a new Residential Companion Use or a change of Use either to or from a Residential Companion Use.

### `expanded_use` — Expanded Use Permit

- Applicants read: Permission for a use the Code normally places in busier districts.
- Reviewer: Planning Board
- Time limits shown: 30 calendar days
- Apply on this site: no (Town Office)
- Applicants read, for `use_permit_decision`: “The Planning Board decides within 30 days of accepting your project.” — approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §16.b.1:

  > Applies to all applications seeking to engage in a new Expanded Use or a change of Use either to or from an Expanded Use.

### `special_permit` — Special Permit

- Applicants read: A Planning Board decision, after a public hearing, on a use the Code allows only case by case.
- Reviewer: Planning Board
- Time limits shown: 30 calendar days, 45 calendar days
- Apply on this site: no (Town Office)
- Applicants read, for `special_permit_review_hearing`: “The Planning Board reviews it and holds a public hearing within 30 days of accepting your project.” — approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Applicants read, for `special_permit_decision`: “The Planning Board decides within 45 days of closing the hearing.” — approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §18.b.1:

  > Special permits may only be requested as specifically authorized by this Code.

### `small_project_plan` — Small Project Plan

- Applicants read: The Code Enforcement Officer's review of a new building, addition or site change up to 10,000 square feet.
- Reviewer: Code Enforcement Officer, who may send it to the Planning Board for a public hearing
- Time limits shown: 10 calendar days
- Apply on this site: yes
- Applicants read, for `small_project_decision`: “The Code Enforcement Officer decides within 10 days of accepting your project.” — approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Ruling (Ben Frey, Planning Board chair, 2026-10-18): Show that §10.c.3 and §11.c.3 let the Code Enforcement Officer send the application to the Planning Board.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §10.b.1:

  > All new buildings and accessory buildings up to 10,000 sf in gross floor area.

### `large_project_plan` — Large Project Plan

- Applicants read: A fuller review of a building over 10,000 square feet, a large parking lot, or a project with big effects on its surroundings.
- Reviewer: Code Enforcement Officer, who may send it to the Planning Board for a public hearing
- Time limits shown: 45 calendar days, 30 calendar days, 30 calendar days
- Apply on this site: no (Town Office)
- Applicants read, for `large_project_ceo_decision`: “The Code Enforcement Officer decides within 45 days of accepting your project.” — approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Applicants read, for `large_project_pb_completeness_hearing`: “If it goes to the Planning Board, the Board checks it is complete and holds a public hearing within 30 days of receiving it.” — approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Applicants read, for `large_project_pb_decision`: “If it goes to the Planning Board, the Board decides within 30 days of closing the hearing.” — approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Ruling (Ben Frey, Planning Board chair, 2026-10-18): Show that §10.c.3 and §11.c.3 let the Code Enforcement Officer send the application to the Planning Board.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §11.b.2:

  > All new buildings and accessory buildings over 10,000 sf in gross floor area.

### `subdivision` — Subdivision

- Applicants read: The Planning Board's review of dividing land into three or more lots within five years, or creating three or more homes.
- Reviewer: Planning Board
- Time limits shown: none
- Apply on this site: no (Town Office)
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §12.b.1:

  > The division of a parcel of land into 3 or more lots within any 5 year period that begins on or after September 23, 1971.

### `entrance_permit` — Driveway and Entrance Permit

- Applicants read: Permission for a new driveway or entrance onto a street or road, or for moving one.
- Reviewer: Code Enforcement Officer
- Time limits shown: none
- Apply on this site: yes
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 3 §13.c.1:

  > The Code Enforcement Officer reviews and approves:
  > a. Driveway construction and relocation permits.
  > b. Entrance permits.
  > c. General maintenance permits where required.

## Rules (`rules.yaml`)

### `civic-land`

- When: `{'eq': ['property.civic', True]}`
- Then: town only
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 2 §5.b.1:

  > Lots designated on the Zoning Map as SD-Civic are municipally owned and not subject to the standards of this Ordinance.

### `use-from-table`

- When: `{'all': [{'has': ['project', 'use']}, {'known': 'use_key'}]}`
- Then: use table
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §15.b.1:

  > Applies to all applications seeking to engage in a new Use or a change of Use on a parcel of land, in a building, or group of buildings.

### `use-not-chosen`

- When: `{'all': [{'has': ['project', 'use']}, {'not': {'known': 'use_key'}}]}`
- Then: Choose the use you have in mind to see which permit the Code calls for.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §15.b.1:

  > Applies to all applications seeking to engage in a new Use or a change of Use on a parcel of land, in a building, or group of buildings.

### `new-homes-residence-use`

- When: `{'all': [{'has': ['project', 'build']}, {'gte': ['building.new_dwelling_units', 1]}]}`
- Then: use table
- Ruling (Ben Frey, Planning Board chair, 2026-10-18): Any home, whether the owner lives in it or rents it out, is the Residence use.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §15.b.1:

  > Applies to all applications seeking to engage in a new Use or a change of Use on a parcel of land, in a building, or group of buildings.

### `new-building-small`

- When: `{'all': [{'has': ['project', 'build']}, {'eq': ['building.kind', 'new']}, {'lte': ['building.gross_floor_area_sf', 10000]}]}`
- Then: names the small project plan
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §10.b.1:

  > All new buildings and accessory buildings up to 10,000 sf in gross floor area.

### `new-building-large`

- When: `{'all': [{'has': ['project', 'build']}, {'eq': ['building.kind', 'new']}, {'gt': ['building.gross_floor_area_sf', 10000]}]}`
- Then: names the large project plan
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §11.b.2:

  > All new buildings and accessory buildings over 10,000 sf in gross floor area.

### `new-building-size-unknown-small`

- When: `{'all': [{'has': ['project', 'build']}, {'eq': ['building.kind', 'new']}, {'not': {'known': 'building.gross_floor_area_sf'}}]}`
- Then: names the small project plan
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §10.b.1:

  > All new buildings and accessory buildings up to 10,000 sf in gross floor area.

### `new-building-size-unknown-large`

- When: `{'all': [{'has': ['project', 'build']}, {'eq': ['building.kind', 'new']}, {'not': {'known': 'building.gross_floor_area_sf'}}]}`
- Then: names the large project plan
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §11.b.2:

  > All new buildings and accessory buildings over 10,000 sf in gross floor area.

### `new-building-size-unknown-note`

- When: `{'all': [{'has': ['project', 'build']}, {'eq': ['building.kind', 'new']}, {'not': {'known': 'building.gross_floor_area_sf'}}]}`
- Then: A new building of up to 10,000 square feet of floor area is a Small Project Plan; a larger one is a Large Project Plan. Count every story.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §10.b.1:

  > All new buildings and accessory buildings up to 10,000 sf in gross floor area.

### `addition-small`

- When: `{'all': [{'has': ['project', 'build']}, {'eq': ['building.kind', 'addition']}, {'lte': ['building.gross_floor_area_sf', 10000]}]}`
- Then: names the small project plan
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §10.b.3:

  > Additions of building components.

### `addition-large`

- When: `{'all': [{'has': ['project', 'build']}, {'eq': ['building.kind', 'addition']}, {'gt': ['building.gross_floor_area_sf', 10000]}]}`
- Then: names the large project plan
- Ruling (Ben Frey, Planning Board chair, 2026-10-18): Additions over 10,000 sf of floor area are a Large Project Plan. §11.b does not list additions, so this rests on §11.b.1 and this ruling.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §11.b.1:

  > Projects that create significant on- or off-site impact.

### `addition-size-unknown-small`

- When: `{'all': [{'has': ['project', 'build']}, {'eq': ['building.kind', 'addition']}, {'not': {'known': 'building.gross_floor_area_sf'}}]}`
- Then: names the small project plan
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §10.b.3:

  > Additions of building components.

### `addition-size-unknown-large`

- When: `{'all': [{'has': ['project', 'build']}, {'eq': ['building.kind', 'addition']}, {'not': {'known': 'building.gross_floor_area_sf'}}]}`
- Then: names the large project plan
- Ruling (Ben Frey, Planning Board chair, 2026-10-18): Additions over 10,000 sf of floor area are a Large Project Plan. §11.b does not list additions, so this rests on §11.b.1 and this ruling.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §11.b.1:

  > Projects that create significant on- or off-site impact.

### `renovation-small`

- When: `{'all': [{'has': ['project', 'build']}, {'eq': ['building.kind', 'renovation']}, {'lte': ['building.total_floor_area_sf', 10000]}]}`
- Then: names the small project plan
- Ruling (Ben Frey, Planning Board chair, 2026-10-18): For renovations, the 10,000 sf line measures the whole building's floor area.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §10.b.2:

  > Building renovations up to 10,000 sf in gross floor area.

### `renovation-large`

- When: `{'all': [{'has': ['project', 'build']}, {'eq': ['building.kind', 'renovation']}, {'gt': ['building.total_floor_area_sf', 10000]}]}`
- Then: names the large project plan
- Ruling (Ben Frey, Planning Board chair, 2026-10-18): For renovations, the 10,000 sf line measures the whole building's floor area.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §11.b.3:

  > Building renovations over 10,000 sf in gross floor area.

### `renovation-size-unknown-small`

- When: `{'all': [{'has': ['project', 'build']}, {'eq': ['building.kind', 'renovation']}, {'not': {'known': 'building.total_floor_area_sf'}}]}`
- Then: names the small project plan
- Ruling (Ben Frey, Planning Board chair, 2026-10-18): For renovations, the 10,000 sf line measures the whole building's floor area.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §10.b.2:

  > Building renovations up to 10,000 sf in gross floor area.

### `renovation-size-unknown-large`

- When: `{'all': [{'has': ['project', 'build']}, {'eq': ['building.kind', 'renovation']}, {'not': {'known': 'building.total_floor_area_sf'}}]}`
- Then: names the large project plan
- Ruling (Ben Frey, Planning Board chair, 2026-10-18): For renovations, the 10,000 sf line measures the whole building's floor area.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §11.b.3:

  > Building renovations over 10,000 sf in gross floor area.

### `site-work`

- When: `{'all': [{'has': ['project', 'build']}, {'eq': ['building.kind', 'site']}, {'not': {'gt': ['building.parking_spaces', 50]}}]}`
- Then: names the small project plan
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §10.b.4:

  > Site improvements.

### `site-work-unknown-parking`

- When: `{'all': [{'has': ['project', 'build']}, {'eq': ['building.kind', 'site']}, {'not': {'known': 'building.parking_spaces'}}]}`
- Then: names the small project plan
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §10.b.4:

  > Site improvements.

### `large-parking`

- When: `{'all': [{'has': ['project', 'build']}, {'eq': ['building.kind', 'site']}, {'gt': ['building.parking_spaces', 50]}]}`
- Then: names the large project plan
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §11.b.4:

  > Site improvements creating more than 50 parking spaces.

### `build-kind-unknown`

- When: `{'all': [{'has': ['project', 'build']}, {'not': {'known': 'building.kind'}}]}`
- Then: Tell us whether you're putting up a new building, adding on, renovating, or working on the site, so we can say which review applies.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §10.b.1:

  > All new buildings and accessory buildings up to 10,000 sf in gross floor area.

### `large-project-impacts`

- When: `{'has': ['project', 'build']}`
- Then: Whatever its size, a project with significant effects — such as blasting, major grading, noise or glare, or work in the road — is a Large Project Plan.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §11.b.1:

  > Projects that create significant on- or off-site impact.

### `three-or-more-new-homes`

- When: `{'all': [{'has': ['project', 'build']}, {'gte': ['building.new_dwelling_units', 3]}]}`
- Then: names the subdivision
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §12.b.3:

  > The construction or placement of 3 or more dwelling units.

### `homes-within-five-years`

- When: `{'all': [{'has': ['project', 'build']}, {'gte': ['building.homes_within_5_years', 3]}]}`
- Then: names the subdivision
- Ruling (Ben Frey, Planning Board chair, 2026-10-18): Homes added on the lot within five years count together toward §12.b.3's three. Counsel to confirm 30-A M.R.S. §4401(4).
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §12.b.3:

  > The construction or placement of 3 or more dwelling units.

### `homes-earlier-unknown`

- When: `{'all': [{'has': ['project', 'build']}, {'gte': ['building.new_dwelling_units', 1]}, {'lt': ['building.new_dwelling_units', 3]}, {'not': {'known': 'building.homes_within_5_years'}}]}`
- Then: names the subdivision
- Ruling (Ben Frey, Planning Board chair, 2026-10-18): Homes added on the lot within five years count together toward §12.b.3's three. Counsel to confirm 30-A M.R.S. §4401(4).
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §12.b.3:

  > The construction or placement of 3 or more dwelling units.

### `divide-three-or-more`

- When: `{'all': [{'has': ['project', 'divide']}, {'gte': ['division.lots_after', 3]}]}`
- Then: names the subdivision
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §12.b.1:

  > The division of a parcel of land into 3 or more lots within any 5 year period that begins on or after September 23, 1971.

### `divide-fewer-none-recent`

- When: `{'all': [{'has': ['project', 'divide']}, {'lt': ['division.lots_after', 3]}, {'eq': ['division.divided_last_5_years', False]}]}`
- Then: Dividing into fewer than three lots, with no other division of the land in the last five years, isn't a subdivision under the Code. Other rules may still apply; the Code Enforcement Officer can tell you what you need.
- Ruling (Ben Frey, Planning Board chair, 2026-10-18): Ask about divisions in the last five years; after an earlier division the Code Enforcement Officer confirms how the lots count.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §12.b.1:

  > The division of a parcel of land into 3 or more lots within any 5 year period that begins on or after September 23, 1971.

### `divide-fewer-recent`

- When: `{'all': [{'has': ['project', 'divide']}, {'lt': ['division.lots_after', 3]}, {'eq': ['division.divided_last_5_years', True]}]}`
- Then: names the subdivision
- Ruling (Ben Frey, Planning Board chair, 2026-10-18): Ask about divisions in the last five years; after an earlier division the Code Enforcement Officer confirms how the lots count.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §12.b.1:

  > The division of a parcel of land into 3 or more lots within any 5 year period that begins on or after September 23, 1971.

### `divide-fewer-recent-note`

- When: `{'all': [{'has': ['project', 'divide']}, {'lt': ['division.lots_after', 3]}, {'eq': ['division.divided_last_5_years', True]}]}`
- Then: Because the land was divided in the last five years, the lots may add up to three or more. The Code Enforcement Officer confirms how they count.
- Ruling (Ben Frey, Planning Board chair, 2026-10-18): Ask about divisions in the last five years; after an earlier division the Code Enforcement Officer confirms how the lots count.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §12.b.1:

  > The division of a parcel of land into 3 or more lots within any 5 year period that begins on or after September 23, 1971.

### `divide-fewer-history-unknown`

- When: `{'all': [{'has': ['project', 'divide']}, {'lt': ['division.lots_after', 3]}, {'not': {'known': 'division.divided_last_5_years'}}]}`
- Then: Dividing into fewer than three lots can still be a subdivision if the land was divided before within the last five years. The Code Enforcement Officer can tell you what applies.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §12.b.1:

  > The division of a parcel of land into 3 or more lots within any 5 year period that begins on or after September 23, 1971.

### `divide-lots-unknown`

- When: `{'all': [{'has': ['project', 'divide']}, {'not': {'known': 'division.lots_after'}}]}`
- Then: names the subdivision
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §12.b.1:

  > The division of a parcel of land into 3 or more lots within any 5 year period that begins on or after September 23, 1971.

### `driveway`

- When: `{'has': ['project', 'driveway']}`
- Then: names the entrance permit
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 3 §7.b.1:

  > Applies to new Driveways and to the relocation of existing Driveways.

### `maine-dot`

- When: `{'all': [{'has': ['project', 'driveway']}, {'any': [{'eq': ['property.on_state_highway', True]}, {'not': {'known': 'property.on_state_highway'}}]}]}`
- Then: If the entrance will be onto a State highway, the Maine Department of Transportation must also approve it. Bring a copy of their permit to the Town.
- Ruling (Ben Frey, Planning Board chair, 2026-10-18): The MaineDOT note applies to any State-owned road, S1 State routes included. §8.c.1's '(R4 or R5)' is an open item.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 3 §12.d.1:

  > An entrance onto a State Highway requires a MaineDOT entrance permit under 23 MRSA §704 in addition to any permit required by this Article.

### `residential-conversion`

- When: `{'all': [{'has': ['project', 'use']}, {'oneof': ['use_key', ['residence', 'rooming_house', 'tourist_rental', 'dormitory']]}]}`
- Then: Dividing a building into three or more homes is a subdivision, reviewed by the Planning Board.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §12.b.2:

  > The division of structures into 3 or more dwelling units.

### `civic-part`

- When: `{'all': [{'has': ['property.district_codes', 'SD-Civic']}, {'ne': ['property.civic', True]}]}`
- Then: Part of this lot is Town-owned land in the Civic district. The answers here are for the rest of the lot.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 2 §5.b.1:

  > Lots designated on the Zoning Map as SD-Civic are municipally owned and not subject to the standards of this Ordinance.

### `something-else`

- When: `{'has': ['project', 'other']}`
- Then: Tell the Code Enforcement Officer what you have in mind; they can say what, if anything, you need.
- Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- Rests on Art. 8 §9.c.1:

  > Applications are required for the following types of projects:
  > a. Small Project Plan
  > b. Large Project Plan
  > c. Subdivision Plan
  > d. Master Plan
  > e. Plan Revision
  > f. Use Permit
  > g. Residential Companion Use Permit
  > h. Expanded Use Permit
  > i. Special Permit
  > j. Variance

## Plain examples for each use (`use-groups.yaml`)

Each use is shown to applicants with its Code name, the Code's definition word for word, and the plain example below.

### A home

- `residence` — **Residence**: A house, apartment or room to live in, whether you live there yourself or rent it out.
  - Code: A dwelling unit used, intended, or designed to be rented, leased, let, or hired out to be occupied for living purposes.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `tourist_rental` — **Tourist Rental**: Renting out a home, or part of one, for stays shorter than 30 days.
  - Code: The rental of a dwelling unit, or a portion of a dwelling unit, on an overnight or short-term basis for less than 30 days at a time.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `bed_breakfast` — **Bed & Breakfast**: Guest rooms for overnight stays in a home where the owner lives.
  - Code: When a permanent resident provides rooms within a single unit residential building for temporary, overnight lodging for compensation in guest rooms with no in-room cooking facilities. A bed and breakfast may include dining facilities and meeting rooms.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `rooming_house` — **Rooming House**: A building where unrelated people rent rooms and share kitchens or bathrooms.
  - Code: A structure occupied, designed, or intended to be occupied by individuals who may share common areas and facilities, but do not form a single household, and do not provide compensation under a single lease for occupancy. A rooming unit provides sleeping accommodations, but no in-room cooking facilities.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `dormitory` — **Dormitory**: Housing run by a school or college for its students or staff.
  - Code: Residential housing exclusively occupied by full or part-time students and/or educational staff and owned or operated by an educational institution.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `mobile_home_park` — **Mobile Home Park**: A park for mobile homes (the Town's Mobile Home Parks Ordinance also applies).
  - Code: See Mobile Home Parks Ordinance
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.

### A shop, office or service

- `retail_service_general` — **Retail & Service, General**: A shop or service you walk into and buy from on the spot, like a store or a hair salon.
  - Code: A business that provides goods or services directly to the consumer, where such goods or services are available for immediate purchase on the premises by the purchaser.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `retail_service_heavy` — **Retail & Service, Heavy**: A business with goods displayed or stored outdoors, like a lumber yard or a garden center.
  - Code: A retail and service business with permanent outdoor display, service, and storage areas, such as vendors of lumber and building supplies, landscaping supplies and equipment, industrial equipment, commercial and recreational vehicles, watercraft, and outdoor structures such as prefabricated sheds, decks and patios, swimming pools, and play equipment.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `retail_firearm_sales_facility` — **Retail Firearm Sales Facility**: A business that displays or sells firearms.
  - Code: A business which publicly displays or offers Firearms, as defined by the Code of Federal Regulations, Title 27, Chapter I, Subchapter C, §53.11 Meaning of terms, for sale to the public, where such Firearms are available for purchase on the premises. Public display or offer does not include online-only displays or offers.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `packaged_liquor` — **Packaged Liquor**: A store selling beer, wine or spirits to take away.
  - Code: Any alcoholic beverage sales establishment involving the sale of alcohol where beer, wine or distilled spirits are sold for off-sale consumption.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `adult_establishment` — **Adult Establishment**: A business selling explicit sexual material, restricted to adults.
  - Code: A business that sells or disseminates explicit sexual material, and at which access to the public display of explicit sexual material is restricted by law to persons 18 years of age or older.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `banking_services` — **Banking Services**: A bank, credit union or other place that lends or keeps money.
  - Code: Uses related to the exchange, lending, borrowing, and safe-keeping of money.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `office_small` — **Office, Small**: A small business office for administration or consulting (not medical).
  - Code: An small office use involves the conduct of business relating to administration, clerical work, and consulting activities, not including medical offices, retail, or service uses. May include single or multiple companies within one unit or building. A small office has up to 5 workers in a single building and 6 parking spaces per lot.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `office_medium` — **Office, Medium**: A mid-sized business office for administration or consulting (not medical).
  - Code: A medium office use involves the conduct of business relating to administration, clerical work, and consulting activities, not including medical offices, retail, or service uses. May include single or multiple companies within one unit or building. A medium office has up to 35 workers in a single building and no parking space limitations.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `office_large` — **Office, Large**: A large business office for administration or consulting (not medical).
  - Code: A medium office use involves the conduct of business relating to administration, clerical work, and consulting activities, not including medical offices, retail, or service uses. May include single or multiple companies within one unit or building. A large office has no maximum number of workers in a single building and no parking space limitations.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `health_care_provider` — **Health Care Provider**: A doctor's, dentist's or therapist's office for outpatient care.
  - Code: An office providing outpatient health services involving the diagnosis and treatment of physical or mental ailments and disorders, including doctors, dentists, mental health practitioners, physical therapists, and their substantial equivalents.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `animal_care_indoor` — **Animal Care, Indoor**: A vet's office or other indoor care for other people's animals.
  - Code: A facility where animals not owned by the proprietor are sheltered and fed, and where all activities are located indoors. Includes veterinarian offices, grooming services, or training services for dogs, cats, and other household pets.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `funeral_services` — **Funeral Services**: A funeral home.
  - Code: A facility where the deceased are prepared for burial display and for rituals before burial or cremation. Such facilities may include chapels and showrooms for the display and sale of caskets, vaults, urns, and other items related to burial services.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `commercial_school` — **Commercial School**: A school teaching particular skills for a fee, like a driving or art school.
  - Code: A school that teaches industrial, clerical, managerial, commercial, artistic, or other select skills; conducts a commercial enterprise, such as a driving school; or a privately operated school that does not offer a complete educational curriculum.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `research_laboratory` — **Research Laboratory**: A lab for research and development.
  - Code: A facility for research and development that does not involve the use of human testing, animal husbandry, incinerators, heavy equipment, mass manufacturing, fabrication, processing, or sale of products.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `vehicle_rental_or_sales` — **Vehicle Rental or Sales**: Selling, leasing or renting cars, motorcycles or similar vehicles.
  - Code: A business that sells, leases, or rents automobiles, vans, three-wheelers, motorcycles, scooters, or other powered personal transportation or conveyance, and which may include on-site facilities for the repair and service of vehicles sold, leased, or rented. This does not include the sale, lease, or rental of recreational vehicles, commercial vehicles, or watercraft, which is considered a heavy retail and service use.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `gas_station` — **Gas Station**: Selling fuel for vehicles.
  - Code: A facility engaged in the retail sales of personal or commercial vehicle fuels.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `car_wash` — **Car Wash**: Washing vehicles, by machine or by hand.
  - Code: An establishment for the washing of motor vehicles, which may employ production-line methods, mechanical devices, staffed hand wash facilities, or unstaffed self-wash facilities.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `drive_through_facility` — **Drive-Through Facility**: Serving customers who stay in their cars, through a window or a machine.
  - Code: A facility that dispenses goods through an attendant window or automated machine to persons remaining in vehicles in a designated drive aisle.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.

### Food, drink or places to stay

- `restaurant_cafe` — **Restaurant & Café**: A restaurant, cafe or takeaway.
  - Code: A business where food and beverages are prepared and served to patrons for consumption either on-premises or off-premises.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `bar_or_tavern` — **Bar or Tavern**: A bar or tavern serving food and alcohol to have there.
  - Code: A business that serves food and alcoholic beverages for on-premises consumption.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `live_entertainment` — **Live Entertainment**: Live music, performance or other entertainment by people present in person.
  - Code: Any activity provided for pleasure, quiet enjoyment, recreation, relaxation, diversion or other similar purpose by a person or persons who are physically present when providing an activity to a patron or group of patrons who are physically present.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `hotel_hostel` — **Hotel & Hostel**: A hotel, inn or hostel.
  - Code: A commercial building(s) with guest rooms designed primarily for sleeping, and usually including a lobby, reception area, conference rooms, recreational amenities, and common kitchen cooking facilities providing meals for paying guests in a dining rooms or restaurants.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `campground` — **Campground**: Sites for tents or recreational vehicles.
  - Code: A site where one or more lots are used, or are intended to be used, by campers with tents or recreational vehicles.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.

### Farming and land

- `commercial_agriculture` — **Commercial Agriculture**: Growing crops or raising livestock to sell.
  - Code: The commercial planting, cultivating, producing, growing, and harvesting of agricultural or horticultural products, the raising of livestock and poultry, and any work performed in conjunction with the above farm operations, including the packing, drying, and storing of products produced on-premises.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `aquaculture` — **Aquaculture**: Farming fish, shellfish or seaweed to sell.
  - Code: The commercial production of cultured fish, shellfish, seaweed, or other marine plants for human and animal consumption, including all cultivating activities occurring at hatcheries or nurseries, from the egg, larval or spore stages to the transfer of the product to a growing site and all cultivating activities occurring on water, from the receipt of fish, shellfish or other marine plants from onshore facilities to the delivery of harvested products to onshore facilities for processing.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `farm_vendor_market` — **Farm/Vendor Market**: A market where several farmers or vendors sell from their own stands.
  - Code: The direct sales of goods and/or products by multiple farmers or vendors from individual booths, tables, or stands, whether indoors or outdoors.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `animal_care_outdoor` — **Animal Care, Outdoor**: Boarding, sheltering or training other people's animals, with outdoor areas.
  - Code: A facility where animals not owned by the proprietor are sheltered and fed. Includes animal rescue shelters, boarding facilities, pet resorts/hotels, or training services for dogs, cats, and other household pets.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `stables_riding_center` — **Stables/Riding Center**: Stables for horses, riding lessons or shows.
  - Code: A structure or land used, designed, and arranged for the care and shelter of equines, for riding, shows, or training, which may include horses not boarded on-site.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `resource_extraction` — **Resource Extraction**: Removing soil, rock, timber or water from the land to sell.
  - Code: Any use that involves the removal of raw materials from the lot, such as soil, rock, timber, or water for commercial activity.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.

### Making, fixing or storing things

- `industrial_artisan` — **Industrial, Artisan**: Small-scale making or assembling, like a woodworking or pottery shop.
  - Code: A manufacturing use involving small-scale production or assembly with no noxious by-products, and which may include a showroom as well as incidental storage, sales, and distribution of products.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `industrial_general` — **Industrial, General**: Light manufacturing, outdoor storage or trucking.
  - Code: Uses that are associated with retail sales, outdoor storage, or light manufacturing of finished or semi-finished products and may include trucking associated with the movement of materials or wholesale distribution.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `industrial_heavy` — **Industrial, Heavy**: Large-scale processing or manufacturing with noise, dust or other effects beyond the lot.
  - Code: The processing, manufacturing, compounding, or storage of materials, products, or energy, where the scale and method of operation regularly produce noise, heat, glare, dust, smoke, fumes, odors, vibration, and that may result in external impacts beyond the lot lines of the property. May regularly employ hazardous material or produce hazardous by-products.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `vehicle_repair` — **Vehicle Repair**: A garage that repairs or services vehicles.
  - Code: A business that repairs, installs, or maintains automobiles, small trucks or vans, motorcycles, motor homes, or recreational vehicles or that wash, clean, or otherwise protect the exterior or interior surfaces of these types of vehicles.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `outdoor_storage` — **Outdoor Storage**: Keeping equipment, vehicles or materials outdoors for a business on the same lot.
  - Code: The outdoor keeping of equipment, vehicles, waste, and any materials associated with uses or activities occurring within buildings on the same lot for a period greater than 48 hours.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `self_storage_facility` — **Self-Storage Facility**: Storage units rented out to the public.
  - Code: A facility where individual secured areas inside a structure are rented for short-term storage of a variety of non-hazardous, non-perishable durable goods and where the lessee has direct access and responsibility for loading and unloading the storage.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `marina_dry_storage` — **Marina, Dry Storage**: Storing boats out of the water, in racks or similar.
  - Code: A site used for the long-term dry storage of recreational watercraft in racks or other storage systems, and which may include ancillary repair facilities for watercraft.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `junk_salvage_yard` — **Junk/Salvage Yard**: A yard that breaks up, sorts or stores scrap or salvage.
  - Code: Outdoor establishments primarily engaged in assembling, breaking up, sorting, and the temporary storage and distribution of recyclable or reusable scrap and waste materials, including auto wreckers engaged in dismantling automobiles for scrap, and the incidental wholesale or retail sales of parts from those vehicles. An area or building where waste or scrap materials are bought, sold, exchanged, stored, baled, packed, disassembled, or handled for reclamation, disposal or other like purposes, including but not limited to scrap iron and other metals, paper, rags, rubber tires, and bottles. A junk or salvage yard or building includes an auto wrecking yard or building.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `recycling_facility` — **Recycling Facility**: A place that takes in and processes recyclable materials.
  - Code: A facility that accepts materials, such as dry paper, glass, cans, or plastics, for storage and processing by power-driven equipment for the subsequent reuse in the secondary materials market.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.

### Recreation, community, care and schools

- `amusement_indoor` — **Amusement, Indoor**: Indoor entertainment or sport, like a cinema or a bowling alley.
  - Code: A commercial facility for spectator and participatory uses conducted within an enclosed building, such as movie theaters, sports arenas, bowling alleys, tumbling centers, skating centers, roller rinks, and pool halls.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `amusement_outdoor` — **Amusement, Outdoor**: Outdoor entertainment or sport, like a fairground or a mini-golf course.
  - Code: A commercial facility for spectator and participatory uses conducted outdoors or within partially enclosed structures, such as fairgrounds, campgrounds, batting cages, drive-in movie theater, recreational vehicle parks, petting zoos, golf courses, miniature golf courses, and amusement parks.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `assembly` — **Assembly**: A place for meetings, services, events or programs.
  - Code: A facility that has organized services, meetings, events, or programs to benefit, educate, entertain, or promote discourse in a public or private setting. Examples include community centers, places of worship, meeting or lecture halls, exhibition rooms, or auditoria.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `cultural_facility` — **Cultural Facility**: A museum, cultural center or historical society open to the public.
  - Code: A facility open to the public for cultural services and exhibitions including, but not limited to, museums, cultural centers, historical societies, and libraries operated by a government or non-profit establishment.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `health_fitness_studio` — **Health/Fitness Studio**: A place for exercise, yoga or similar classes.
  - Code: A facility that provides interactive classes, personal or small group instruction, or other activities related to the improvement of the body, mind, and soul.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `marina_recreation` — **Marina, Recreation**: Docks or moorings for recreational boats, on the water.
  - Code: A facility that has frontage on navigable water and allows for the short- or long-term docking and mooring of boats and that may provide supply, repair, and other services.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `private_club_or_lodge` — **Private Club or Lodge**: A club or lodge open to members or invited guests.
  - Code: A facility operated for an organization, which is open to people upon invitation, nomination, or payment of fees or dues, for social, recreational, and/or entertainment activities.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `college_university` — **College/University**: A college or university.
  - Code: A post-secondary institution for higher learning that grants associate, bachelor, masters, or doctoral degrees, and theological schools.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `primary_secondary_school` — **Primary/Secondary School**: An elementary, middle or high school.
  - Code: A public, private, or parochial institution with a primary function of offering instruction at any of all primary or secondary education levels, inclusive of kindergarten through the 12th grade. This use shall not include businesses that offer exclusively recreational classes, such as art classes, musical instruction, or other similar classes open to the general public.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `day_care_center` — **Day Care Center**: Licensed day care run alongside a home.
  - Code: A residential companion use that provides licensed care in a protective setting for children or elderly or disabled adults.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `day_care_facility` — **Day Care Facility**: A licensed day care for children or adults.
  - Code: A facility where licensed care, protection, and supervision is provided in a protective setting for children or adults, with or without compensation, on a regular basis away from a primary residence.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `hospital` — **Hospital**: A hospital.
  - Code: A facility that provides health, medical, or surgical care to the sick or injured and contains offices integral to function of the facility.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `human_service_facility` — **Human Service Facility**: Services for people who need help because of age, disability, addiction, illness or injury.
  - Code: An establishment that provides services to persons in need of assistance due to age, physical or mental disability, addiction, illness, or injury, that does not provide residential dwelling units.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `residential_care_facility` — **Residential Care Facility**: A licensed home providing round-the-clock care.
  - Code: A licensed care facility that provides 24-hour medical or non-medical care to persons in need of personal services, supervision, protection, or assistance essential for sustaining the activities of daily living. Residential care facilities include nursing homes, independent living, assisted living, continuum of care, and hospice facilities.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `food_pantry` — **Food Pantry**: A not-for-profit giving out food or essentials free or at low cost.
  - Code: A not-for-profit use that distributes or facilitates the giving of food, clothing, and/or other essential items at no charge or for less than fair market value to persons in need of assistance.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.

### Transport, parking and utilities

- `dispatch_service` — **Dispatch Service**: A base for taxis, ambulances, tow trucks or buses.
  - Code: The storage and dispatch of ambulances, taxis, limousines, armored cars, tow trucks, buses, and similar vehicles for specialized transportation, including where ambulance crews not located at a hospital or fire department stand by for emergency calls, ancillary professional offices, and/or minor vehicle service and maintenance repair.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `district_energy_system` — **District Energy System**: An energy system shared by several properties.
  - Code: A community-based energy system shared by property owners for common use, or managed by a homeowners' association, institution, or similar organization.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `utilities_services` — **Utilities & Services**: Buildings or structures for electricity, internet, gas, water or similar services.
  - Code: Buildings and structures that provide or facilitate the transmission of services consumed by the public including electricity, Internet, natural gas, water, and sewage.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.
- `paid_parking_lot` — **Paid Parking Lot**: A parking lot open to the public for a fee.
  - Code: A non-accessory parking lot made available to the general public in exchange for a fee.
  - Approved by Ben Frey, Planning Board chair, on 2026-10-20.

