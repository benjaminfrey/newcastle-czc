# Application forms: approval record (adopted-v1.0)

Every section and field of the three application forms, with what applicants read, when each question is asked, the Code text it rests on, and its approval. Production refuses a form while any of its entries is a draft.

**Every entry is approved.**

To approve an entry, change `status: draft` to `status: approved` with `approved_by` and `approved_on` in its YAML file (`portal/api/portal_api/forms/definitions/forms/`).

## Decisions so far

- **Fields come from the Town's current Planning Application packet** (Cover Sheet, Use Form, Building Form, Components Section), read from the scanned 2025 applications in `docs/`. The Entrance / Driveway Form is new, drafted from Art. 3 §§7–8 and §12.
- **Buildings and components repeat**: the form prints one Building Form per building and one Components Section per addition, porch, deck or other component.
- **Signatures, dates and "Name (print)"** are filled when the applicant signs and submits (Milestone 6).
- **Redesign (briefs approved 2026-10-23 and 2026-10-24): steps, screens and controls.** Each form is grouped into a few steps ("Step:" below) and asked one question per screen; fields marked "Screen:" are asked together on one screen. "Control:" names the control drawn (switch, stepper, slider, chips, picker, tiles). A switch's starting position is written as an answer marked as the form's, and the applicant sees it set.
- **Proposed with the redesign, for approval:** (1) a detached garage or shed is a building, chosen by its type ("A smaller building that goes with a home"), which the wizard asks first; an attached garage stays an addition, and the "garage attached or detached" question is gone; (2) the four window walls are sliders, still percentages, labelled with the street side as well as the compass point; (3) roof slope is picked (Flat, 2/12 to 12/12, Steeper), exterior finish is chips with an Other field, "attached to" picks one of the application's buildings, and the entrance's road picks one along the lot; (4) the four setbacks are entered around a not-to-scale drawing of the lot; (5) each building, and each addition or attached garage with walls, is asked which way its front faces, so the walls can be named by the street side (the chair's ruling, 2026-10-24).

## The chair's rulings (2026-10-23)

1. **Site plan or sketch for a Small Project Plan.** Optional. Applicants are asked for one (a hand drawing is fine) and told staff may ask for it.
2. **Building Form on a Small Project Plan.** Asked only when the work includes a building: a new building, an addition or a renovation. A project that is only site work, or only a change to a nonconforming lot or use, has no Building Form.
3. **"Standard Met?" column.** Dropped. The new form has no pass/fail column; the CEO's conclusions belong in the decision. The District Standard column returns as Milestone 6's standards-check flags.
4. **Special Use Building.** Kept: the building types follow Art. 5 §1.c, all nine. The Code does not define Special Use Building (open item for the next amendment).
5. **Names on the Cover Sheet.** Kept: the Applicant, Property Owner and Agent blocks each have a Name line.
6. **The packet.** The scanned 2025 forms are complete: the Cover Sheet, Use Form, Building Form (one page) and Components Section are the whole packet for these applications.

## The chair's decisions (2026-10-28)

The chair approved every entry, taking these eleven decisions:

1. **The five proposals from the redesign.** Approved, all five (listed under Decisions so far).
2. **A building's name.** Optional; an unnamed building shows as "Building 2".
3. **Homes in each building.** Asked of every building type, starting at 0: an apartment over a garage or in a barn counts toward subdivision.
4. **Stories.** Capped at 4, matching the Building Form's four floor heights; a taller building talks to the Town Office.
5. **Spelling.** "story", "Fiber-cement" and "sq ft" everywhere applicants read.
6. **Four wording fixes.** The road-frontage, building-type, lot-size and "Something else" help, as proposed.
7. **Exterior finish choices.** Approved as listed.
8. **The parts of a project.** Approved.
9. **The questions only a project asks.** Approved.
10. **The time limits in plain words.** Approved (listed in the screener rules memo).
11. **The rest of the four forms.** Approved as written.

## Cover Sheet (part of every application)

### Location of Proposed Project (`location`)

- Step: Your lot
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Map / Lot (`map_lot`)

- Source: from the property lookup (staff confirm) — `map_lot`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Street Address (`street_address`)

- Source: from the property lookup (staff confirm) — `location` (the applicant may correct it)
- Applicants read: “What is the street address of the property?”
- Help: For example "461 Sheepscot Road". If the land has no address yet, write the road it's on.
- Answer: text; required
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

#### Deed Book (`deed_book`)

- Source: asked in the wizard
- Applicants read: “If you know it, what is the book number of your deed?”
- Help: It's printed on your deed from the Lincoln County Registry of Deeds. Staff can look it up if you don't have it.
- Answer: text; optional; “I don't know yet” allowed
- Card: asked with the others on `deed`, which asks “Where is your deed recorded?”
- Short name on its card: “Deed book”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

#### Page (`deed_page`)

- Source: asked in the wizard
- Applicants read: “And the page number of your deed?”
- Help: It's printed next to the book number.
- Answer: text; optional; “I don't know yet” allowed
- Card: asked with the others on `deed`, which asks “Where is your deed recorded?”
- Short name on its card: “Page”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

### Applicant (`applicant`)

- Step: About you
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Name (`applicant_name`)

- Source: from the applicant's sign-in — `name`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Email (`applicant_email`)

- Source: from the applicant's sign-in — `email`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Phone (`applicant_phone`)

- Source: from the applicant's sign-in — `phone`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Address (`applicant_address`)

- Source: from the applicant's sign-in — `mailing_address`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Applicant is the Property Owner (`applicant_is_owner`)

- Source: asked in the wizard
- Applicants read: “Do you own this property?”
- Help: Choose No if you're a builder or someone else applying for the owner.
- Answer: yesno; required
- Control: switch (starts on)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

#### Agent (`has_agent`)

- Source: asked in the wizard
- Applicants read: “Is someone else helping with this, like a builder or surveyor?”
- Help: If you choose Yes, the Town will also contact them.
- Answer: yesno; required
- Control: switch (starts off)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

### Property Owner (if different) (`owner`)

- Step: About you
- Printed and asked only when “Applicant is the Property Owner” is No
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Name (`owner_name`)

- Source: asked in the wizard
- Applicants read: “What is the property owner's full name?”
- Help: If a company or trust owns it, give its name.
- Answer: text; required
- Card: asked with the others on `owner`, which asks “Who owns the property?”
- Short name on its card: “Owner's name”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

#### Email (`owner_email`)

- Source: asked in the wizard
- Applicants read: “What is the owner's email address?”
- Answer: text; required; “I don't know yet” allowed
- Card: asked with the others on `owner`, which asks “Who owns the property?”
- Short name on its card: “Email”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

#### Phone (`owner_phone`)

- Source: asked in the wizard
- Applicants read: “What is the owner's phone number?”
- Answer: text; required; “I don't know yet” allowed
- Card: asked with the others on `owner`, which asks “Who owns the property?”
- Short name on its card: “Phone”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

#### Address (`owner_address`)

- Source: asked in the wizard
- Applicants read: “What is the owner's mailing address?”
- Answer: text; required
- Card: asked with the others on `owner`, which asks “Who owns the property?”
- Short name on its card: “Mailing address”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

### Agent (if applicable) (`agent`)

- Step: About you
- Printed and asked only when “Agent” is Yes
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Name (`agent_name`)

- Source: asked in the wizard
- Applicants read: “What is their name, or their company's name?”
- Answer: text; required
- Card: asked with the others on `agent`, which asks “Who is helping?”
- Short name on its card: “Name or company”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

#### Email (`agent_email`)

- Source: asked in the wizard
- Applicants read: “What is their email address?”
- Answer: text; required; “I don't know yet” allowed
- Card: asked with the others on `agent`, which asks “Who is helping?”
- Short name on its card: “Email”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

#### Phone (`agent_phone`)

- Source: asked in the wizard
- Applicants read: “What is their phone number?”
- Answer: text; required; “I don't know yet” allowed
- Card: asked with the others on `agent`, which asks “Who is helping?”
- Short name on its card: “Phone”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

#### Address (`agent_address`)

- Source: asked in the wizard
- Applicants read: “What is their mailing address?”
- Answer: text; required; “I don't know yet” allowed
- Card: asked with the others on `agent`, which asks “Who is helping?”
- Short name on its card: “Mailing address”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

### Site Information (existing) (`site`)

- Step: Your lot
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Zoning District (`zoning_district`)

- Source: from the property lookup (staff confirm) — `districts`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Lot Area (acres) (`lot_area`)

- Source: from the property lookup (staff confirm) — `acres` (the applicant may correct it)
- Applicants read: “How big is your lot, in acres?”
- Help: Change it if your deed or a survey says otherwise.
- Answer: number (acres), 0–5000; required
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

#### Lot Width (ft) (`lot_width`)

- Source: asked in the wizard
- Applicants read: “How wide is your lot, in feet?”
- Help: Measure at the widest point between the side lot lines, anywhere from the front lot line back to the farthest a building may sit from the road (the district's maximum front setback).
- Answer: number (ft), 0–50000; required; “I don't know yet” allowed
- Card: asked with the others on `lot_size`, which asks “How big is your lot?”
- Short name on its card: “Width”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

#### Street Frontage (ft) (`street_frontage`)

- Source: from the property lookup (staff confirm) — `streets` (the applicant may correct it)
- Applicants read: “How many feet of your lot run along the road?”
- Help: We've filled in what the Town's map shows. If the lot is on more than one road, add them together.
- Answer: number (ft), 0–50000; required; “I don't know yet” allowed
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

#### Lot Depth (ft) (`lot_depth`)

- Source: asked in the wizard
- Applicants read: “How deep is your lot, from the road to the back lot line, in feet?”
- Answer: number (ft), 0–50000; required; “I don't know yet” allowed
- Card: asked with the others on `lot_size`, which asks “How big is your lot?”
- Short name on its card: “Depth”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

#### Number of Existing Dwelling Units (`existing_dwelling_units`)

- Source: asked in the wizard
- Applicants read: “How many homes are on the property now?”
- Help: Count each house, apartment or other separate home (the Code calls each one a dwelling unit). Enter 0 if there are none.
- Answer: number, 0–500; required
- Control: stepper
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

### Certification (`certification`)

- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Applicant Signature (`signature`)

- Source: filled when the applicant signs and submits (M6)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Date (`signature_date`)

- Source: filled when the applicant signs and submits (M6)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Name (print) (`signature_name`)

- Source: filled when the applicant signs and submits (M6)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

### Official Use Only (`office`)

- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Date Received (`date_received`)

- Source: staff fill this in
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

## Use Permit Application

`use_permit` version 1; the Cover Sheet comes first.

### Proposed Project (`use_header`)

- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Applicant Name (`use_applicant_name`)

- Source: copied from another field — `applicant_name`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Street Address (`use_street_address`)

- Source: copied from another field — `street_address`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Map / Lot (`use_map_lot`)

- Source: copied from another field — `map_lot`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

### Existing (`existing`)

- Step: Uses today
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Existing Use(s) (`existing_uses`)

- Source: asked in the wizard
- Applicants read: “What is the property used for now?”
- Help: Pick each use from the Code's list. If the land is empty, or nothing fits, leave this blank and say so in the next question.
- Answer: uses; optional
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §15.b.1:

  > Applies to all applications seeking to engage in a new Use or a change of Use on a parcel of land, in a building, or group of buildings.

#### Description (`existing_description`)

- Source: asked in the wizard
- Applicants read: “In a sentence or two, how is the property used now?”
- Help: For example "Our home, with a two-car garage we use for storage."
- Answer: longtext; required
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §15.b.1:

  > Applies to all applications seeking to engage in a new Use or a change of Use on a parcel of land, in a building, or group of buildings.

### Proposed (`proposed`)

- Step: Your plan
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Uses to be Established (`proposed_uses`)

- Source: asked in the wizard
- Applicants read: “Which use or uses do you want to start?”
- Help: If you came here from "Do I need a permit?", we've filled in the use you picked. You can add others.
- Answer: uses; required
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §15.b.1:

  > Applies to all applications seeking to engage in a new Use or a change of Use on a parcel of land, in a building, or group of buildings.

#### Description (`proposed_description`)

- Source: asked in the wizard
- Applicants read: “What do you plan to do there?”
- Help: Say what will happen there, in which building, and roughly how much: for example "Repair lawn and garden equipment in my 30 by 40 ft garage, by appointment, two or three customers a week."
- Answer: longtext; required
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §15.b.1:

  > Applies to all applications seeking to engage in a new Use or a change of Use on a parcel of land, in a building, or group of buildings.

#### Uses to be Discontinued (`discontinued_uses`)

- Source: asked in the wizard
- Applicants read: “Will any use that's there now stop?”
- Help: Pick each use that will stop. Leave this blank if nothing will stop.
- Answer: uses; optional
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §15.b.1:

  > Applies to all applications seeking to engage in a new Use or a change of Use on a parcel of land, in a building, or group of buildings.

#### Description of Uses to be Discontinued (`discontinued_description`)

- Source: asked in the wizard
- Applicants read: “What will stop, and when?”
- Answer: longtext; optional
- Asked only when “Uses to be Discontinued” has an answer
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §15.b.1:

  > Applies to all applications seeking to engage in a new Use or a change of Use on a parcel of land, in a building, or group of buildings.

### Attachments (`use_documents_section`)

- Step: Photos and plans
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Other relevant documentation (`use_documents`)

- Source: asked in the wizard
- Applicants read: “Add anything else that would help, like photos, a floor plan or a business plan.”
- Help: PDF, JPEG, PNG or HEIC files up to 25 MB each. This is optional, but staff may ask for more.
- Answer: upload; optional
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

### Use Form Certification (`use_certification`)

- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Applicant Signature (`use_signature`)

- Source: filled when the applicant signs and submits (M6)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Date (`use_signature_date`)

- Source: filled when the applicant signs and submits (M6)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Name (print) (`use_signature_name`)

- Source: filled when the applicant signs and submits (M6)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

### Use Form — Official Use Only (`use_office`)

- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Permit Type Required (`permit_type_required`)

- Source: staff fill this in
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

## Small Project Plan Application

`small_project_plan` version 1; the Cover Sheet comes first.

### Your Project (`project`)

- Step: The work
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Type of project (`work_kinds`)

- Source: worked out from the project's parts (never asked) — `work_kinds`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §10.b.1:

  > All new buildings and accessory buildings up to 10,000 sf in gross floor area.

#### Project description (`project_description`)

- Source: asked in the wizard
- Applicants read: “In a few sentences, what will you build or change?”
- Answer: longtext; required
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

#### Site plan or sketch (`site_plan`)

- Source: asked in the wizard
- Applicants read: “Add a site plan or a sketch showing where the work is on your lot.”
- Help: A hand drawing is fine. Show the lot lines, the road, the buildings and their distances from the lot lines.
- Answer: upload; optional
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

### Building Form (`building`)

- Step: Buildings
- Repeats: one per building (1 to 20); the wizard offers “Add another building”
- Printed and asked only when (“Type of project” includes New building or accessory building) or (“Type of project” includes Addition of building components) or (“Type of project” includes Building renovation)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Map / Lot (`building_map_lot`)

- Source: copied from another field — `map_lot`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Street Address (`building_address`)

- Source: copied from another field — `street_address`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Zoning District (`building_district`)

- Source: copied from another field — `zoning_district`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Building reference (name) (`building_name`)

- Source: asked in the wizard
- Applicants read: “What do you call this building?”
- Help: For example "house", "barn" or "new garage".
- Answer: text; optional
- Card: asked with the others on `about`, which asks “What is this building?”
- Short name on its card: “What you call it”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

#### Only being renovated, not changing size or location (`renovation_only`)

- Source: asked in the wizard
- Applicants read: “Is it only being renovated?”
- Help: Choose Yes if the building keeps its size and place.
- Answer: yesno; required
- Copied by “Copy Building 1”
- Control: switch (starts off)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §10.b.2:

  > Building renovations up to 10,000 sf in gross floor area.

### Building Location (proposed) (`building_location`)

- Step: Buildings
- Repeats: one per building (1 to 20); the wizard offers “Add another building”
- Printed and asked only when (“Type of project” includes New building or accessory building) or (“Type of project” includes Addition of building components) or (“Type of project” includes Building renovation)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Setback from front lot line (`setback_front`)

- Source: asked in the wizard
- Applicants read: “How far will the building be from the front lot line, the one along the road?”
- Help: Measure in feet from the lot line to the closest part of the building.
- Answer: number (ft), 0–50000; required; “I don't know yet” allowed
- Card: asked with the others on `setbacks` (lot-diagram drawing)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 2 §3.c.3:

  > All primary buildings must comply with required front, side, and rear setback ranges.

#### Setback from side lot line (`setback_side_1`)

- Source: asked in the wizard
- Applicants read: “How far will it be from the nearest side lot line?”
- Help: In feet, from the lot line to the closest part of the building.
- Answer: number (ft), 0–50000; required; “I don't know yet” allowed
- Card: asked with the others on `setbacks` (lot-diagram drawing)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 2 §3.c.3:

  > All primary buildings must comply with required front, side, and rear setback ranges.

#### Setback from other side lot line (`setback_side_2`)

- Source: asked in the wizard
- Applicants read: “How far will it be from the other side lot line?”
- Answer: number (ft), 0–50000; required; “I don't know yet” allowed
- Card: asked with the others on `setbacks` (lot-diagram drawing)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 2 §3.c.3:

  > All primary buildings must comply with required front, side, and rear setback ranges.

#### Setback from rear lot line (`setback_rear`)

- Source: asked in the wizard
- Applicants read: “How far will it be from the back lot line?”
- Answer: number (ft), 0–50000; required; “I don't know yet” allowed
- Card: asked with the others on `setbacks` (lot-diagram drawing)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 2 §3.c.3:

  > All primary buildings must comply with required front, side, and rear setback ranges.

### Building Details (proposed) (`building_details`)

- Step: Buildings
- Repeats: one per building (1 to 20); the wizard offers “Add another building”
- Printed and asked only when (“Type of project” includes New building or accessory building) or (“Type of project” includes Addition of building components) or (“Type of project” includes Building renovation)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Building type (`building_class`)

- Source: asked in the wizard
- Applicants read: “Which best describes this building?”
- Help: If you're not sure, choose "I don't know yet". Staff will help you choose.
- Answer: choice; required; “I don't know yet” allowed
  - Residential Building — applicants read “A home: a house, duplex or apartment building”
  - Single Unit Commercial Building — applicants read “A building for one business”
  - Multi-unit Commercial Building — applicants read “A building for several businesses”
  - Mixed-Use Building — applicants read “A building with homes and businesses together”
  - Residential Accessory Building — applicants read “A smaller building that goes with a home, like a garage or shed”
  - Commercial Accessory Building — applicants read “A smaller building that goes with a business”
  - General Accessory Building — applicants read “A smaller building that could serve a home or a business”
  - Special Use Building — applicants read “A Special Use Building (staff can help you decide)”
  - Agricultural Building — applicants read “A farm building, like a barn, stable or greenhouse”
- Copied by “Copy Building 1”
- Control: building-type
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 5 §1.c.1:

  > Buildings shall be classified as Primary or Accessory as follows:
  > a. Primary Buildings are;
  > b. Accessory Buildings are;
  > c. The following buildings may be Primary or Accessory Buildings:

#### Proposed number of dwelling units (`dwelling_units`)

- Source: asked in the wizard
- Applicants read: “How many homes will this building have?”
- Help: Count each separate home with its own kitchen. Enter 0 if none.
- Answer: number, 0–500; required
- Card: asked with the others on `about`, which asks “What is this building?”
- Short name on its card: “Homes in it”
- Control: stepper
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

### Main Building Mass Details (`building_mass`)

- Step: Buildings
- Repeats: one per building (1 to 20); the wizard offers “Add another building”
- Printed and asked only when (“Type of project” includes New building or accessory building) or (“Type of project” includes Addition of building components) or (“Type of project” includes Building renovation)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Width of Main Building Mass (`mass_width`)

- Source: asked in the wizard
- Applicants read: “How wide is the main part of the building, in feet?”
- Help: The "main building mass" is the main rectangular part of the building, not counting additions, porches or decks. Width is measured along the side facing the road.
- Answer: number (ft), 0–2000; required; “I don't know yet” allowed
- Card: asked with the others on `size`, which asks “How big is the building?”
- Short name on its card: “Width”
- Copied by “Copy Building 1”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 5 §3.c.2:

  > Each Primary Building and each Accessory Building must be comprised of a Main Building Mass with a rectangular form and a single allowed roof type.

#### Depth of Main Building Mass (`mass_depth`)

- Source: asked in the wizard
- Applicants read: “How deep is the main part of the building, front to back, in feet?”
- Answer: number (ft), 0–2000; required; “I don't know yet” allowed
- Card: asked with the others on `size`, which asks “How big is the building?”
- Short name on its card: “Depth”
- Copied by “Copy Building 1”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 5 §3.c.2:

  > Each Primary Building and each Accessory Building must be comprised of a Main Building Mass with a rectangular form and a single allowed roof type.

#### Total number of stories (`stories`)

- Source: asked in the wizard
- Applicants read: “How many stories (floors above ground) will it have?”
- Help: Don't count a basement or living space inside the roof. If it will have more than four, talk to the Town Office.
- Answer: number, 1–4; required; “I don't know yet” allowed
- Card: asked with the others on `size`, which asks “How big is the building?”
- Short name on its card: “Floors above ground”
- Copied by “Copy Building 1”
- Control: stepper
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 5 §3.c.2:

  > Each Primary Building and each Accessory Building must be comprised of a Main Building Mass with a rectangular form and a single allowed roof type.

#### Floor Area of Main Building Mass (`floor_area`)

- Source: asked in the wizard
- Applicants read: “What is the floor area of the main part of the building, in square feet?”
- Help: Add up every story of the main part. Space inside the roof doesn't count.
- Answer: number (sq ft), 0–1000000; required; “I don't know yet” allowed
- Card: asked with the others on `size`, which asks “How big is the building?”
- Short name on its card: “Floor area”
- Copied by “Copy Building 1”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 5 §3.c.4:

  > The standards set forth in the Permitted Building tables under Article 2 - District Standards for Building Width, Building Depth, and Total Square Feet apply only to the Main Building Mass of Primary Buildings and Accessory Buildings.

#### Elevation of first (ground) floor (`first_floor_elevation`)

- Source: asked in the wizard
- Applicants read: “How high is the first floor above the ground at the front of the building, in feet?”
- Help: Measure from the average ground level at the front to the top of the first floor.
- Answer: number (ft), 0–30; required; “I don't know yet” allowed
- Card: asked with the others on `size`, which asks “How big is the building?”
- Short name on its card: “First floor above the ground”
- Copied by “Copy Building 1”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 5 §4.c.4:

  > First floor elevation is measured from the average ground level at the front of the building to the top of the finished floor of the first story of a building.

#### First floor height (`floor_height_1`)

- Source: asked in the wizard
- Applicants read: “How tall is the first story, floor to floor, in feet?”
- Help: From the surface of the floor to the surface of the floor above (or to the top of the wall if there's no floor above).
- Answer: number (ft), 0–50; required; “I don't know yet” allowed
- Card: asked with the others on `size`, which asks “How big is the building?”
- Short name on its card: “First floor height”
- Copied by “Copy Building 1”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 5 §7.c.2:

  > Story height is measured from the surface of any floor to the surface of the floor above it or, if there is no floor above, from the surface of the floor to the top of the wall plate.

#### Second floor height (`floor_height_2`)

- Source: asked in the wizard
- Applicants read: “How tall is the second story, in feet?”
- Answer: number (ft), 0–50; required; “I don't know yet” allowed
- Card: asked with the others on `size`, which asks “How big is the building?”
- Short name on its card: “Second floor height”
- Copied by “Copy Building 1”
- Asked only when “Total number of stories” (this building) is 2 or more
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 5 §7.c.2:

  > Story height is measured from the surface of any floor to the surface of the floor above it or, if there is no floor above, from the surface of the floor to the top of the wall plate.

#### Third floor height (`floor_height_3`)

- Source: asked in the wizard
- Applicants read: “How tall is the third story, in feet?”
- Answer: number (ft), 0–50; required; “I don't know yet” allowed
- Card: asked with the others on `size`, which asks “How big is the building?”
- Short name on its card: “Third floor height”
- Copied by “Copy Building 1”
- Asked only when “Total number of stories” (this building) is 3 or more
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 5 §7.c.2:

  > Story height is measured from the surface of any floor to the surface of the floor above it or, if there is no floor above, from the surface of the floor to the top of the wall plate.

#### Fourth floor height (`floor_height_4`)

- Source: asked in the wizard
- Applicants read: “How tall is the fourth story, in feet?”
- Answer: number (ft), 0–50; required; “I don't know yet” allowed
- Card: asked with the others on `size`, which asks “How big is the building?”
- Short name on its card: “Fourth floor height”
- Copied by “Copy Building 1”
- Asked only when “Total number of stories” (this building) is 4 or more
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 5 §7.c.2:

  > Story height is measured from the surface of any floor to the surface of the floor above it or, if there is no floor above, from the surface of the floor to the top of the wall plate.

#### Roof Style (`roof_style`)

- Source: asked in the wizard
- Applicants read: “What shape is the roof?”
- Answer: choice; required; “I don't know yet” allowed
  - Gable — applicants read “Gable: two slopes meeting at a peak”
  - Mansard — applicants read “Mansard: steep lower slopes with a flatter top”
  - Gambrel — applicants read “Gambrel: a barn-style roof with two slopes on each side”
  - Hipped — applicants read “Hipped: slopes on all four sides”
  - Shed — applicants read “Shed: a single slope”
- Card: asked with the others on `roof`, which asks “What shape is the roof?”
- Short name on its card: “Shape”
- Copied by “Copy Building 1”
- Control: tiles
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §5.c.2:

  > Each primary building, accessory building, or component may only have one roof.

#### Roof Slope on Main Building Mass (`roof_slope`)

- Source: asked in the wizard
- Applicants read: “How steep is the roof?”
- Help: Pick the pitch: how many inches the roof rises for every 12 inches across.
- Answer: choice; required; “I don't know yet” allowed
  - Flat (under 2/12) — applicants read “Flat (under 2/12)”
  - 2/12 — applicants read “2/12”
  - 3/12 — applicants read “3/12”
  - 4/12 — applicants read “4/12”
  - 5/12 — applicants read “5/12”
  - 6/12 — applicants read “6/12”
  - 7/12 — applicants read “7/12”
  - 8/12 — applicants read “8/12”
  - 9/12 — applicants read “9/12”
  - 10/12 — applicants read “10/12”
  - 11/12 — applicants read “11/12”
  - 12/12 — applicants read “12/12”
  - Steeper than 12/12 — applicants read “Steeper than 12/12”
- Card: asked with the others on `roof`, which asks “What shape is the roof?”
- Short name on its card: “Slope”
- Copied by “Copy Building 1”
- Control: picker
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §5.c.2:

  > Each primary building, accessory building, or component may only have one roof.

#### Exterior finish material (`exterior_finish`)

- Source: asked in the wizard
- Applicants read: “What will the outside walls and roof be covered with?”
- Help: Choose all that apply.
- Answer: multichoice; required; “I don't know yet” allowed
  - Clapboard — applicants read “Clapboard”
  - Wood shingle — applicants read “Wood shingle”
  - Vinyl siding — applicants read “Vinyl siding”
  - Fiber-cement siding — applicants read “Fiber-cement siding”
  - Brick — applicants read “Brick”
  - Stone — applicants read “Stone”
  - Board-and-batten — applicants read “Board-and-batten”
  - Metal siding — applicants read “Metal siding”
  - Asphalt shingle roof — applicants read “Asphalt shingle roof”
  - Metal roof — applicants read “Metal roof”
  - Slate roof — applicants read “Slate roof”
  - Other — applicants read “Something else”
- Card: asked with the others on `outside`, which asks “What will the outside walls and roof be covered with?”
- Short name on its card: “Materials”
- Copied by “Copy Building 1”
- Control: chips
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §5.c.5:

  > Pitched roofs, if provided, must be clad with wood shingles, asphalt shingles, slate tile, metal, or have the appearance of natural materials.

#### Other exterior finish (`exterior_finish_other`)

- Source: asked in the wizard
- Applicants read: “What other material?”
- Answer: text; required
- Card: asked with the others on `outside`, which asks “What will the outside walls and roof be covered with?”
- Short name on its card: “Other material”
- Copied by “Copy Building 1”
- Asked only when “Exterior finish material” (this building) includes Other
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §5.c.5:

  > Pitched roofs, if provided, must be clad with wood shingles, asphalt shingles, slate tile, metal, or have the appearance of natural materials.

### Windows & Doors - Main Building Mass (`building_windows`)

- Step: Buildings
- Repeats: one per building (1 to 20); the wizard offers “Add another building”
- Printed and asked only when (“Type of project” includes New building or accessory building) or (“Type of project” includes Addition of building components) or (“Type of project” includes Building renovation)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Direction the front faces (`front_facing`)

- Source: asked in the wizard
- Applicants read: “Which way does the front of the building face?”
- Help: The front is the side facing the road. Pick the closest direction.
- Answer: choice; required; “I don't know yet” allowed
  - North — applicants read “North” (icon `arrow-up`)
  - East — applicants read “East” (icon `arrow-right`)
  - South — applicants read “South” (icon `arrow-down`)
  - West — applicants read “West” (icon `arrow-left`)
- Card: asked with the others on `walls` (compass drawing)
- Control: tiles
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §6.c.2:

  > The required window and door percentages apply to the total area of each story of each building facade as measured from the surface of the floor of that story, to the surface of the next floor above; or, if there is no floor above, to either the top of the wall plate, or the base of the buildings eaves, whichever is shorter.

#### North facing facade % (`windows_north`)

- Source: asked in the wizard
- Applicants read: “North wall”
- Help: About what share of this wall is windows and doors?
- Answer: number (%), 0–100; required; “I don't know yet” allowed
- Card: asked with the others on `walls` (compass drawing)
- Control: slider
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §6.c.2:

  > The required window and door percentages apply to the total area of each story of each building facade as measured from the surface of the floor of that story, to the surface of the next floor above; or, if there is no floor above, to either the top of the wall plate, or the base of the buildings eaves, whichever is shorter.

#### East facing facade % (`windows_east`)

- Source: asked in the wizard
- Applicants read: “East wall”
- Help: About what share of this wall is windows and doors?
- Answer: number (%), 0–100; required; “I don't know yet” allowed
- Card: asked with the others on `walls` (compass drawing)
- Control: slider
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §6.c.2:

  > The required window and door percentages apply to the total area of each story of each building facade as measured from the surface of the floor of that story, to the surface of the next floor above; or, if there is no floor above, to either the top of the wall plate, or the base of the buildings eaves, whichever is shorter.

#### South facing facade % (`windows_south`)

- Source: asked in the wizard
- Applicants read: “South wall”
- Help: About what share of this wall is windows and doors?
- Answer: number (%), 0–100; required; “I don't know yet” allowed
- Card: asked with the others on `walls` (compass drawing)
- Control: slider
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §6.c.2:

  > The required window and door percentages apply to the total area of each story of each building facade as measured from the surface of the floor of that story, to the surface of the next floor above; or, if there is no floor above, to either the top of the wall plate, or the base of the buildings eaves, whichever is shorter.

#### West facing facade % (`windows_west`)

- Source: asked in the wizard
- Applicants read: “West wall”
- Help: About what share of this wall is windows and doors?
- Answer: number (%), 0–100; required; “I don't know yet” allowed
- Card: asked with the others on `walls` (compass drawing)
- Control: slider
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §6.c.2:

  > The required window and door percentages apply to the total area of each story of each building facade as measured from the surface of the floor of that story, to the surface of the next floor above; or, if there is no floor above, to either the top of the wall plate, or the base of the buildings eaves, whichever is shorter.

### Components Section (`component`)

- Step: Additions, porches and decks
- Repeats: one per component (0 to 30); the wizard offers “Add an addition, porch or deck”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Component (`component_kind`)

- Source: asked in the wizard
- Applicants read: “What are you adding or changing?”
- Answer: choice; required
  - Addition — applicants read “An addition to a building” (icon `home-plus`)
  - Garage (attached) — applicants read “An attached garage” (icon `car-garage`)
  - Porch — applicants read “A porch” (icon `armchair`)
  - Deck — applicants read “A deck” (icon `stairs`)
  - Patio — applicants read “A patio” (icon `square`)
  - Other Architectural Component — applicants read “Something else, like a dormer, bay window or cupola” (icon `dots`)
- Card: asked with the others on `kind`, which asks “What are you adding or changing?”
- Short name on its card: “What it is”
- Control: tiles
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §2.a.1:

  > To provide a clear and flexible system for enabling the construction of new buildings and the expansion and modification of existing buildings.

#### Name of other architectural component (`component_other_name`)

- Source: asked in the wizard
- Applicants read: “What is it called?”
- Answer: text; required
- Card: asked with the others on `kind`, which asks “What are you adding or changing?”
- Short name on its card: “What it's called”
- Asked only when “Component” (this component) is Other Architectural Component
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §2.a.1:

  > To provide a clear and flexible system for enabling the construction of new buildings and the expansion and modification of existing buildings.

#### Only being renovated, not changing size or location (`component_renovation_only`)

- Source: asked in the wizard
- Applicants read: “Is it only being renovated?”
- Help: Choose Yes if it keeps its size and place.
- Answer: yesno; required
- Control: switch (starts off)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §10.b.2:

  > Building renovations up to 10,000 sf in gross floor area.

#### Building attached to (`attached_to`)

- Source: asked in the wizard
- Applicants read: “Which building is it attached to?”
- Help: Choose the building it's attached to, or Free-standing.
- Answer: text; required
- Control: building-picker
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 5 §3.d.1:

  > Components may attach to primary and accessory buildings.

#### Width (`component_width`)

- Source: asked in the wizard
- Applicants read: “How wide is it, in feet?”
- Answer: number (ft), 0–2000; required; “I don't know yet” allowed
- Card: asked with the others on `size`, which asks “How big is it?”
- Short name on its card: “Width”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §2.a.1:

  > To provide a clear and flexible system for enabling the construction of new buildings and the expansion and modification of existing buildings.

#### Depth (Length for a Patio) (`component_depth`)

- Source: asked in the wizard
- Applicants read: “How deep is it, or how long for a patio, in feet?”
- Answer: number (ft), 0–2000; required; “I don't know yet” allowed
- Card: asked with the others on `size`, which asks “How big is it?”
- Short name on its card: “Depth”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §2.a.1:

  > To provide a clear and flexible system for enabling the construction of new buildings and the expansion and modification of existing buildings.

#### Height (`component_height`)

- Source: asked in the wizard
- Applicants read: “How tall is it, from the ground to its highest point, in feet?”
- Answer: number (ft), 0–200; required; “I don't know yet” allowed
- Card: asked with the others on `size`, which asks “How big is it?”
- Short name on its card: “Height”
- Asked only when “Component” (this component) is not Patio
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §2.a.1:

  > To provide a clear and flexible system for enabling the construction of new buildings and the expansion and modification of existing buildings.

#### Floor area added (`added_floor_area`)

- Source: asked in the wizard
- Applicants read: “How much floor area will the addition add, in square feet?”
- Help: Count every story. Choose "I don't know yet" if you aren't sure.
- Answer: number (sq ft), 0–1000000; required; “I don't know yet” allowed
- Card: asked with the others on `size`, which asks “How big is it?”
- Short name on its card: “Floor area added”
- Asked only when “Component” (this component) is not Patio
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §10.b.3:

  > Additions of building components.

#### Roof Style on Component (`component_roof_style`)

- Source: asked in the wizard
- Applicants read: “What shape is its roof?”
- Answer: choice; required; “I don't know yet” allowed
  - Gable — applicants read “Gable: two slopes meeting at a peak”
  - Mansard — applicants read “Mansard: steep lower slopes with a flatter top”
  - Gambrel — applicants read “Gambrel: a barn-style roof with two slopes on each side”
  - Hipped — applicants read “Hipped: slopes on all four sides”
  - Shed — applicants read “Shed: a single slope”
- Card: asked with the others on `roof`, which asks “What shape is its roof?”
- Short name on its card: “Shape”
- Control: tiles
- Asked only when “Component” (this component) is Addition or Garage (attached)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §5.c.2:

  > Each primary building, accessory building, or component may only have one roof.

#### Roof Slope (`component_roof_slope`)

- Source: asked in the wizard
- Applicants read: “How steep is its roof?”
- Help: Pick the pitch: how many inches the roof rises for every 12 inches across.
- Answer: choice; required; “I don't know yet” allowed
  - Flat (under 2/12) — applicants read “Flat (under 2/12)”
  - 2/12 — applicants read “2/12”
  - 3/12 — applicants read “3/12”
  - 4/12 — applicants read “4/12”
  - 5/12 — applicants read “5/12”
  - 6/12 — applicants read “6/12”
  - 7/12 — applicants read “7/12”
  - 8/12 — applicants read “8/12”
  - 9/12 — applicants read “9/12”
  - 10/12 — applicants read “10/12”
  - 11/12 — applicants read “11/12”
  - 12/12 — applicants read “12/12”
  - Steeper than 12/12 — applicants read “Steeper than 12/12”
- Card: asked with the others on `roof`, which asks “What shape is its roof?”
- Short name on its card: “Slope”
- Control: picker
- Asked only when “Component” (this component) is Addition or Garage (attached)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §5.c.2:

  > Each primary building, accessory building, or component may only have one roof.

#### Exterior finish material (`component_finish`)

- Source: asked in the wizard
- Applicants read: “What will its outside walls and roof be covered with?”
- Help: Choose all that apply.
- Answer: multichoice; required; “I don't know yet” allowed
  - Clapboard — applicants read “Clapboard”
  - Wood shingle — applicants read “Wood shingle”
  - Vinyl siding — applicants read “Vinyl siding”
  - Fiber-cement siding — applicants read “Fiber-cement siding”
  - Brick — applicants read “Brick”
  - Stone — applicants read “Stone”
  - Board-and-batten — applicants read “Board-and-batten”
  - Metal siding — applicants read “Metal siding”
  - Asphalt shingle roof — applicants read “Asphalt shingle roof”
  - Metal roof — applicants read “Metal roof”
  - Slate roof — applicants read “Slate roof”
  - Other — applicants read “Something else”
- Card: asked with the others on `outside`, which asks “What will its outside walls and roof be covered with?”
- Short name on its card: “Materials”
- Control: chips
- Asked only when “Component” (this component) is Addition or Garage (attached)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §5.c.5:

  > Pitched roofs, if provided, must be clad with wood shingles, asphalt shingles, slate tile, metal, or have the appearance of natural materials.

#### Other exterior finish (`component_finish_other`)

- Source: asked in the wizard
- Applicants read: “What other material?”
- Answer: text; required
- Card: asked with the others on `outside`, which asks “What will its outside walls and roof be covered with?”
- Short name on its card: “Other material”
- Asked only when (“Component” (this component) is Addition or Garage (attached)) and (“Exterior finish material” (this component) includes Other)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §5.c.5:

  > Pitched roofs, if provided, must be clad with wood shingles, asphalt shingles, slate tile, metal, or have the appearance of natural materials.

#### Direction the front faces (`component_front_facing`)

- Source: asked in the wizard
- Applicants read: “Which way does the front of the building face?”
- Help: The front is the side facing the road. Pick the closest direction.
- Answer: choice; required; “I don't know yet” allowed
  - North — applicants read “North” (icon `arrow-up`)
  - East — applicants read “East” (icon `arrow-right`)
  - South — applicants read “South” (icon `arrow-down`)
  - West — applicants read “West” (icon `arrow-left`)
- Card: asked with the others on `walls` (compass drawing)
- Control: tiles
- Asked only when “Component” (this component) is Addition or Garage (attached)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §6.c.2:

  > The required window and door percentages apply to the total area of each story of each building facade as measured from the surface of the floor of that story, to the surface of the next floor above; or, if there is no floor above, to either the top of the wall plate, or the base of the buildings eaves, whichever is shorter.

#### North facing facade % (`component_windows_north`)

- Source: asked in the wizard
- Applicants read: “North wall”
- Help: About what share of this wall is windows and doors?
- Answer: number (%), 0–100; required; “I don't know yet” allowed
- Card: asked with the others on `walls` (compass drawing)
- Control: slider
- Asked only when “Component” (this component) is Addition or Garage (attached)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §6.c.2:

  > The required window and door percentages apply to the total area of each story of each building facade as measured from the surface of the floor of that story, to the surface of the next floor above; or, if there is no floor above, to either the top of the wall plate, or the base of the buildings eaves, whichever is shorter.

#### East facing facade % (`component_windows_east`)

- Source: asked in the wizard
- Applicants read: “East wall”
- Help: About what share of this wall is windows and doors?
- Answer: number (%), 0–100; required; “I don't know yet” allowed
- Card: asked with the others on `walls` (compass drawing)
- Control: slider
- Asked only when “Component” (this component) is Addition or Garage (attached)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §6.c.2:

  > The required window and door percentages apply to the total area of each story of each building facade as measured from the surface of the floor of that story, to the surface of the next floor above; or, if there is no floor above, to either the top of the wall plate, or the base of the buildings eaves, whichever is shorter.

#### South facing facade % (`component_windows_south`)

- Source: asked in the wizard
- Applicants read: “South wall”
- Help: About what share of this wall is windows and doors?
- Answer: number (%), 0–100; required; “I don't know yet” allowed
- Card: asked with the others on `walls` (compass drawing)
- Control: slider
- Asked only when “Component” (this component) is Addition or Garage (attached)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §6.c.2:

  > The required window and door percentages apply to the total area of each story of each building facade as measured from the surface of the floor of that story, to the surface of the next floor above; or, if there is no floor above, to either the top of the wall plate, or the base of the buildings eaves, whichever is shorter.

#### West facing facade % (`component_windows_west`)

- Source: asked in the wizard
- Applicants read: “West wall”
- Help: About what share of this wall is windows and doors?
- Answer: number (%), 0–100; required; “I don't know yet” allowed
- Card: asked with the others on `walls` (compass drawing)
- Control: slider
- Asked only when “Component” (this component) is Addition or Garage (attached)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 6 §6.c.2:

  > The required window and door percentages apply to the total area of each story of each building facade as measured from the surface of the floor of that story, to the surface of the next floor above; or, if there is no floor above, to either the top of the wall plate, or the base of the buildings eaves, whichever is shorter.

## Entrance / Driveway Permit Application

`entrance_permit` version 1; the Cover Sheet comes first.

### Entrance / Driveway Form (`entrance`)

- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Streets and Roads along the lot (Town map) (`lot_streets`)

- Source: from the property lookup (staff confirm) — `streets`
- Step: The driveway
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Street or Road the entrance is on (`entrance_street`)

- Source: asked in the wizard
- Applicants read: “Which road will the driveway connect to?”
- Help: Choose the road the driveway will join.
- Answer: text; required
- Step: The driveway
- Control: street-picker
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 3 §8.b.1:

  > Applies to any new access to a lot from a Street or Road, whether utilizing a Driveway or a parking lot.

#### Work proposed (`entrance_work`)

- Source: asked in the wizard
- Applicants read: “What are you doing?”
- Answer: choice; required
  - New Driveway — applicants read “Putting in a new driveway”
  - Relocation of an existing Driveway — applicants read “Moving an existing driveway”
  - New entrance to a parking lot — applicants read “Making a new entrance to a parking lot”
- Step: The driveway
- Control: segmented
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 3 §7.b.1:

  > Applies to new Driveways and to the relocation of existing Driveways.

#### Single-family dwellings served (`homes_single_family`)

- Source: asked in the wizard
- Applicants read: “How many single-family homes will use this driveway?”
- Help: Count homes on your lot and any other lot that will share the driveway.
- Answer: number, 0–500; required
- Step: The driveway
- Card: asked with the others on `homes`, which asks “How many homes will use this driveway?”
- Short name on its card: “Single-family homes”
- Control: stepper
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 3 §7.c.7:

  > A Driveway that is expanded or altered to serve more than two single-family dwellings, or more than one two-family dwelling, whether on one lot or on several, is no longer a Driveway under this Section. The access way is thereafter a Street or Road and shall be improved to its assigned Thoroughfare Type as provided in Section 7.F.

#### Two-family dwellings served (`homes_two_family`)

- Source: asked in the wizard
- Applicants read: “How many two-family homes (duplexes) will use it?”
- Answer: number, 0–500; required
- Step: The driveway
- Card: asked with the others on `homes`, which asks “How many homes will use this driveway?”
- Short name on its card: “Two-family homes”
- Control: stepper
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 3 §7.c.7:

  > A Driveway that is expanded or altered to serve more than two single-family dwellings, or more than one two-family dwelling, whether on one lot or on several, is no longer a Driveway under this Section. The access way is thereafter a Street or Road and shall be improved to its assigned Thoroughfare Type as provided in Section 7.F.

#### Shared with an abutting lot (`shared_driveway`)

- Source: asked in the wizard
- Applicants read: “Will a neighboring lot share this driveway?”
- Answer: yesno; required
- Step: The driveway
- Control: switch (starts off)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 3 §7.c.3:

  > Abutting lots may share a Driveway provided that an access easement exists between all owners and the shared Driveway complies with the entrance standards in Section 8.

#### Access easement (`access_easement`)

- Source: asked in the wizard
- Applicants read: “Add a copy of the access easement between the owners.”
- Help: The Code allows a shared driveway where there is an access easement between all the owners.
- Answer: upload; optional
- Step: The driveway
- Asked only when “Shared with an abutting lot” is Yes
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 3 §7.c.3:

  > Abutting lots may share a Driveway provided that an access easement exists between all owners and the shared Driveway complies with the entrance standards in Section 8.

#### Location of the entrance (`entrance_location`)

- Source: asked in the wizard
- Applicants read: “Tap the map where the driveway will meet the road.”
- Answer: point; required
- Step: Where it joins the road
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 3 §8.d.2:

  > No part of the entrance shall extend beyond the property lot frontage.

#### Driveway width (ft) (`driveway_width`)

- Source: asked in the wizard
- Applicants read: “How wide will the driveway be, in feet?”
- Answer: number (ft), 0–200; required; “I don't know yet” allowed
- Step: Where it joins the road
- Card: asked with the others on `driveway`, which asks “What will the driveway be like?”
- Short name on its card: “Width”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 3 §7.e.1:

  > Driveway maximum width is calibrated by District as follows:
  > a. D1, D2, R1/R2/R3 corridors: 24 ft max
  > b. D3, D4, S3 corridors: 20 ft max
  > c. D5, D6, S1/S2 corridors: 12 ft max within the frontage zone (may flare beyond the frontage zone)
  > d. SD-Highway Commercial, SD-Rural Highway: 30 ft max with MaineDOT entrance permit

#### Slope of the first 20 ft (%) (`first_20ft_slope`)

- Source: asked in the wizard
- Applicants read: “How steep is the first 20 feet of driveway, up or down from the road, as a percent?”
- Help: A 1-foot rise over 20 feet is 5%. If it's about level, enter 0.
- Answer: number (%), 0–25; required; “I don't know yet” allowed
- Step: Where it joins the road
- Card: asked with the others on `driveway`, which asks “What will the driveway be like?”
- Short name on its card: “Slope of the first 20 ft”
- Control: slider
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 3 §7.d.2:

  > Driveways must be constructed to prevent water run-off onto the adjacent Street or Road.

#### Angle of intersection with the Street or Road (degrees) (`entrance_angle`)

- Source: asked in the wizard
- Applicants read: “At what angle will the driveway meet the road, in degrees?”
- Help: Straight in, square to the road, is 90 degrees.
- Answer: number (degrees), 0–90; required; “I don't know yet” allowed
- Step: Where it joins the road
- Card: asked with the others on `driveway`, which asks “What will the driveway be like?”
- Short name on its card: “Angle to the road”
- Control: slider
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 3 §8.e.1:

  > Entrances shall intersect the adjacent Street or Road at a horizontal angle of 90 degrees.

#### Sight distance, looking left (ft) (`sight_distance_left`)

- Source: asked in the wizard
- Applicants read: “Standing where the driveway will join the road, how far can you see to the left, in feet?”
- Help: Look along the road for the farthest point where you could see an oncoming car.
- Answer: number (ft), 0–5000; required; “I don't know yet” allowed
- Step: Safety at the road
- Card: asked with the others on `sight`, which asks “How far can you see from the driveway?”
- Short name on its card: “Seeing left”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 3 §8.f.1:

  > All entrances shall be so located that vehicles approaching or using the entrance:
  > a. Shall be able to obtain unobstructed sight distance in both directions along the adjacent Street or Road in accordance with Table 3.2 Sight Distance.
  > b. Shall be able to maneuver safely without interference with traffic.

#### Sight distance, looking right (ft) (`sight_distance_right`)

- Source: asked in the wizard
- Applicants read: “And how far to the right, in feet?”
- Answer: number (ft), 0–5000; required; “I don't know yet” allowed
- Step: Safety at the road
- Card: asked with the others on `sight`, which asks “How far can you see from the driveway?”
- Short name on its card: “Seeing right”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 3 §8.f.1:

  > All entrances shall be so located that vehicles approaching or using the entrance:
  > a. Shall be able to obtain unobstructed sight distance in both directions along the adjacent Street or Road in accordance with Table 3.2 Sight Distance.
  > b. Shall be able to maneuver safely without interference with traffic.

#### Distance to the nearest intersection (ft) (`intersection_distance`)

- Source: asked in the wizard
- Applicants read: “How far will the driveway be from the nearest road intersection, in feet?”
- Answer: number (ft), 0–50000; required; “I don't know yet” allowed
- Step: Safety at the road
- Card: asked with the others on `sight`, which asks “How far can you see from the driveway?”
- Short name on its card: “To the nearest intersection”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 3 §8.f.2:

  > Entrances shall not be constructed within the following distances of an intersection:
  > a. 75 ft of an un-signaled intersection.
  > b. 125 ft of a signaled intersection.

#### Nearest intersection is signaled (`intersection_signal`)

- Source: asked in the wizard
- Applicants read: “Does that intersection have a traffic light?”
- Answer: yesno; required; “I don't know yet” allowed
- Step: Safety at the road
- Card: asked with the others on `sight`, which asks “How far can you see from the driveway?”
- Short name on its card: “A traffic light there”
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 3 §8.f.2:

  > Entrances shall not be constructed within the following distances of an intersection:
  > a. 75 ft of an un-signaled intersection.
  > b. 125 ft of a signaled intersection.

#### Ditch along the road at the entrance (`roadside_ditch`)

- Source: asked in the wizard
- Applicants read: “Is there a ditch along the road where the driveway will go?”
- Help: If there is, a culvert may be needed under the driveway.
- Answer: yesno; required; “I don't know yet” allowed
- Step: Safety at the road
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 3 §7.d.3:

  > Where the Permitting Authority determines that a Driveway culvert is necessary, the applicant shall bear the burden of the cost for the culvert installation, which shall be constructed to the standards of Section 10.

#### MaineDOT entrance permit (`mainedot_permit`)

- Source: asked in the wizard
- Applicants read: “Do you have a MaineDOT entrance permit for this driveway?”
- Help: A driveway onto a State road also needs a permit from the Maine Department of Transportation. The Town needs a copy before it issues the Zoning Permit.
- Answer: choice; required
  - Received — applicants read “Yes, I have it”
  - Applied for — applicants read “I've applied for it”
  - Not yet applied for — applicants read “Not yet”
- Step: State permit and sketch
- Control: segmented
- Asked only when the lot is not known to be off State roads (on a State road, or unknown)
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 3 §12.d.1:

  > An entrance onto a State Highway requires a MaineDOT entrance permit under 23 MRSA §704 in addition to any permit required by this Article.

#### Copy of MaineDOT entrance permit (`mainedot_copy`)

- Source: asked in the wizard
- Applicants read: “Add a copy of your MaineDOT entrance permit.”
- Answer: upload; optional
- Step: State permit and sketch
- Asked only when “MaineDOT entrance permit” is Received
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 3 §12.d.2:

  > The applicant shall submit a copy of the MaineDOT entrance permit to the Permitting Authority before the Zoning Permit is issued.

#### Sketch (`entrance_sketch`)

- Source: asked in the wizard
- Applicants read: “Add a sketch of the driveway, if you have one.”
- Help: A hand drawing is fine. Show the road, the lot lines and the driveway.
- Answer: upload; optional
- Step: State permit and sketch
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

## Project questions

`project_questions` version 1; the Cover Sheet comes first.

### Renovation (`renovation`)

- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Building to be renovated (`renovation_building`)

- Source: asked in the wizard
- Applicants read: “Which building are you renovating?”
- Help: For example, the house or the barn.
- Answer: text; required
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §10.b.2:

  > Building renovations up to 10,000 sf in gross floor area.

#### Floor area of the whole building (`renovation_total_floor_area`)

- Source: asked in the wizard
- Applicants read: “What is the floor area of the whole building, in square feet?”
- Help: Count every story. Choose "I don't know yet" if you aren't sure.
- Answer: number (sq ft), 0–1000000; required; “I don't know yet” allowed
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §10.b.2:

  > Building renovations up to 10,000 sf in gross floor area.

### Site work (`site_work`)

- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Parking spaces (`parking_spaces`)

- Source: asked in the wizard
- Applicants read: “How many parking spaces will there be?”
- Help: Enter 0 if there's no parking.
- Answer: number, 0–2000; required; “I don't know yet” allowed
- Control: stepper
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §10.b.4:

  > Site improvements.

### Dividing land (`division`)

- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Lots after the division (`lots_after`)

- Source: asked in the wizard
- Applicants read: “How many lots will there be afterwards?”
- Answer: number, 1–500; required; “I don't know yet” allowed
- Control: stepper
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §12.b.1:

  > The division of a parcel of land into 3 or more lots within any 5 year period that begins on or after September 23, 1971.

#### Divided in the last five years (`divided_last_5_years`)

- Source: asked in the wizard
- Applicants read: “Has this land been divided in the last five years?”
- Help: Lots made within five years count together.
- Answer: choice; required
  - Yes — applicants read “Yes”
  - No — applicants read “No”
  - Not known — applicants read “I don't know”
- Control: tiles
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §12.b.1:

  > The division of a parcel of land into 3 or more lots within any 5 year period that begins on or after September 23, 1971.

### Something else (`other`)

- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### What the applicant has in mind (`other_description`)

- Source: asked in the wizard
- Applicants read: “Tell us what you have in mind.”
- Help: A few sentences is enough. Staff will tell you what else they need.
- Answer: longtext; required
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §2.a.2:

  > Applications must include all necessary information and plan contents for the Permitting Authority to determine compliance with this Code.

### Homes added before this project (`project_homes`)

- Printed and asked only when `new_homes_total` is 1 or more
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

#### Homes added on this lot in the last five years (`homes_last_5_years`)

- Source: asked in the wizard
- Applicants read: “How many homes were added on this lot in the last five years, before this project?”
- Help: Homes added within five years count together. Enter 0 if none.
- Answer: number, 0–500; required; “I don't know yet” allowed
- Control: stepper
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.
- Rests on Art. 8 §12.b.3:

  > The construction or placement of 3 or more dwelling units.

## Parts (`parts.yaml`)

A project is made of parts; each asks the form sections listed and sets the rules' inputs (projects brief §6.1). "Type of project" prints from the parts.

### A new building (`building`)

- Dashboard row: New buildings; icon `building-cottage`; repeats (one per building or addition)
- Asks: Small Project Plan Application — `building`, `building_location`, `building_details`, `building_mass`, `building_windows`
- Rule input: `project` = `build`, `building.kind` = `new`
- Sets for the rules: `building.gross_floor_area_sf` from `floor_area`
- Sets for the rules: `building.new_dwelling_units` from `dwelling_units`
- Prints as Type of project: `new_building`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

### An addition, porch or deck (`addition`)

- Dashboard row: Additions; icon `home-plus`; repeats (one per building or addition)
- Asks: Small Project Plan Application — `component`
- Rule input: `project` = `build`, `building.kind` = `addition`
- Sets for the rules: `building.gross_floor_area_sf` from `added_floor_area`
- Prints as Type of project: `addition`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

### Renovating a building (`renovation`)

- Dashboard row: Renovation; icon `paint`
- Asks: Project questions — `renovation`
- Rule input: `project` = `build`, `building.kind` = `renovation`
- Sets for the rules: `building.total_floor_area_sf` from `renovation_total_floor_area`
- Prints as Type of project: `renovation`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

### Site work (parking, grading, landscaping) (`site`)

- Dashboard row: Site work; icon `shovel`
- Asks: Project questions — `site_work`
- Rule input: `project` = `build`, `building.kind` = `site`
- Sets for the rules: `building.parking_spaces` from `parking_spaces`
- Prints as Type of project: `site`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

### Start or change a use (`use`)

- Dashboard row: Uses; icon `building-store`
- Asks: Use Permit Application — `existing`, `proposed`, `use_documents_section`
- Rule input: `project` = `use`
- Sets for the rules: `use_key` from `proposed_uses`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

### A driveway (`driveway`)

- Dashboard row: Driveway; icon `road`
- Asks: Entrance / Driveway Permit Application — `entrance`
- Rule input: `project` = `driveway`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

### Divide land (`divide`)

- Dashboard row: Dividing land; icon `layout-grid`
- Asks: Project questions — `division`
- Rule input: `project` = `divide`
- Sets for the rules: `division.lots_after` from `lots_after`
- Sets for the rules: `division.divided_last_5_years` from `divided_last_5_years`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

### Something else (`other`)

- Dashboard row: Something else; icon `help-circle`
- Asks: Project questions — `other`
- Rule input: `project` = `other`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

### About the work (`the_work`)

- Asks: Small Project Plan Application — `project` when the project has any of building, addition, renovation, site
- Asks: Project questions — `project_homes` when the project has any of building
- Sets for the rules: `building.homes_added_last_5_years` from `homes_last_5_years`
- Approved by Ben Frey, Planning Board chair, on 2026-10-28.

