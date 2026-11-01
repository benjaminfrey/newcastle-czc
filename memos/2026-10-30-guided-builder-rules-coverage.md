# Rules coverage for the guided builder

*Generated 2026-10-30 from the pinned ruleset `adopted-v1.0` by `python -m portal_api.standards audit`.*

This memo says which of the Code's district standards the guided builder can check today, which it can't and why, and the questions only the chair can answer. It never fills in a value the Code doesn't state.

## 1. Summary

452 standards across 13 districts: 148 from the district pages' dimension panels and 304 from the Permitted Buildings tables.

| Status | Count |
|---|---|
| can be checked (`checkable`) | 111 |
| no minimum or maximum stated (`needs_qualifier`) | 196 |
| no unit stated (`needs_unit`) | 7 |
| not set for this district (`not_established`) | 98 |
| unresolved in the ruleset (`unresolved`) | 2 |
| not a number (who decides) (`not_a_number`) | 38 |

## 2. District by district

### D1 - Rural

| Building | Field | Raw | Status | Bounds |
|---|---|---|---|---|
|  | Width | 100 ft min | checkable | at least 100 ft |
|  | Depth | n/a | not_established |  |
|  | Lot Area | n/a | not_established |  |
|  | Primary Frontage Line Length | 250 ft min | checkable | at least 250 ft |
|  | Primary Front Setback | 20 ft min | checkable | at least 20 ft |
|  | Secondary Front Setback | 20 ft min | checkable | at least 20 ft |
|  | Side Setback | 15 ft min | checkable | at least 15 ft |
|  | Rear Setback | 15 ft min | checkable | at least 15 ft |
|  | Primary Front Setback | 10 ft min | checkable | at least 10 ft |
|  | Secondary Front Setback | 10 ft min | checkable | at least 10 ft |
|  | Side Setback | 5 ft min | checkable | at least 5 ft |
|  | Rear Setback | 5 ft min | checkable | at least 5 ft |
| Residential | Permitting Authority | CEO | not_a_number |  |
| General Accessory | Permitting Authority | CEO | not_a_number |  |
| Agricultural Use | Permitting Authority | CEO | not_a_number |  |
| Residential | Building Width | 50 ft | needs_qualifier |  |
| General Accessory | Building Width | 30 ft | needs_qualifier |  |
| Agricultural Use | Building Width | - | not_established |  |
| Residential | Building Depth | 50 ft | needs_qualifier |  |
| General Accessory | Building Depth | 40 ft | needs_qualifier |  |
| Agricultural Use | Building Depth | - | not_established |  |
| Residential | Building Floor Area | - | not_established |  |
| General Accessory | Building Floor Area | - | not_established |  |
| Agricultural Use | Building Floor Area | - | not_established |  |
| Residential | Total Stories | 2 | needs_qualifier |  |
| General Accessory | Total Stories | 1 | needs_qualifier |  |
| Agricultural Use | Total Stories | - | not_established |  |
| Residential | First Floor Height | 12 ft | needs_qualifier |  |
| General Accessory | First Floor Height | 16 ft | needs_qualifier |  |
| Agricultural Use | First Floor Height | - | not_established |  |
| Residential | Upper Floor Height | 10 ft | needs_qualifier |  |
| General Accessory | Upper Floor Height | 10 ft | needs_qualifier |  |
| Agricultural Use | Upper Floor Height | - | not_established |  |
| Residential | Number of Units | - | not_established |  |
| General Accessory | Number of Units | 2 | needs_qualifier |  |
| Agricultural Use | Number of Units | - | not_established |  |

### D2 - Neighborhood Residential

| Building | Field | Raw | Status | Bounds |
|---|---|---|---|---|
|  | Width | 80 ft min, 200 ft max | checkable | at least 80 ft, at most 200 ft |
|  | Depth | n/a | not_established |  |
|  | Lot Area | n/a | not_established |  |
|  | Primary Front Setback | 20 ft min | checkable | at least 20 ft |
|  | Secondary Front Setback | 20 ft min | checkable | at least 20 ft |
|  | Side Setback | 12 ft min | checkable | at least 12 ft |
|  | Rear Setback | 10 ft min | checkable | at least 10 ft |
|  | Frontage Zone Setback | n/a | not_established |  |
|  | Primary Front Setback | 20 ft min | checkable | at least 20 ft |
|  | Secondary Front Setback | 20 ft min | checkable | at least 20 ft |
|  | Side Setback | 5 ft min | checkable | at least 5 ft |
|  | Rear Setback | 5 ft min | checkable | at least 5 ft |
| Residential | Permitting Authority | CEO | not_a_number |  |
| Mixed-Use | Permitting Authority | Planning Board | not_a_number |  |
| Residential Accessory | Permitting Authority | CEO | not_a_number |  |
| Residential | Building Width | 75 ft | needs_qualifier |  |
| Mixed-Use | Building Width | 50 ft | needs_qualifier |  |
| Residential Accessory | Building Width | 30 ft | needs_qualifier |  |
| Residential | Building Depth | 50 ft | needs_qualifier |  |
| Mixed-Use | Building Depth | 50 ft | needs_qualifier |  |
| Residential Accessory | Building Depth | 40 ft | needs_qualifier |  |
| Residential | Building Floor Area | - | not_established |  |
| Mixed-Use | Building Floor Area | - | not_established |  |
| Residential Accessory | Building Floor Area | - | not_established |  |
| Residential | Total Stories | 2 | needs_qualifier |  |
| Mixed-Use | Total Stories | 2 | needs_qualifier |  |
| Residential Accessory | Total Stories | 1 | needs_qualifier |  |
| Residential | First Floor Height | 12 ft | needs_qualifier |  |
| Mixed-Use | First Floor Height | 12 ft | needs_qualifier |  |
| Residential Accessory | First Floor Height | 16 ft | needs_qualifier |  |
| Residential | Upper Floor Height | 10 ft | needs_qualifier |  |
| Mixed-Use | Upper Floor Height | 10 ft | needs_qualifier |  |
| Residential Accessory | Upper Floor Height | 8 ft | needs_qualifier |  |
| Residential | Number of Units | - | not_established |  |
| Mixed-Use | Number of Units | - | not_established |  |
| Residential Accessory | Number of Units | 1 | needs_qualifier |  |

### D3 - Neighborhood Business

| Building | Field | Raw | Status | Bounds |
|---|---|---|---|---|
|  | Width | 60 ft min, 200 ft max | checkable | at least 60 ft, at most 200 ft |
|  | Depth | n/a | not_established |  |
|  | Lot Area | n/a | not_established |  |
|  | Primary Front Setback | 20 ft min, 75 ft max | checkable | at least 20 ft, at most 75 ft |
|  | Secondary Front Setback | 20 ft min | checkable | at least 20 ft |
|  | Side Setback | 12 ft min | checkable | at least 12 ft |
|  | Rear Setback | 10 ft min | checkable | at least 10 ft |
|  | Frontage Zone Setback | 4 ft min | checkable | at least 4 ft |
|  | Primary Front Setback | 20 ft min | checkable | at least 20 ft |
|  | Secondary Front Setback | 20 ft min | checkable | at least 20 ft |
|  | Side Setback | 12 ft min | checkable | at least 12 ft |
|  | Rear Setback | 10 ft min | checkable | at least 10 ft |
| Residential | Permitting Authority | Planning Board | not_a_number |  |
| Mixed-Use | Permitting Authority | Planning Board | not_a_number |  |
| Residential Accessory | Permitting Authority | CEO | not_a_number |  |
| Commercial Accessory | Permitting Authority | Planning Board | not_a_number |  |
| Residential | Building Width | 50 ft | needs_qualifier |  |
| Mixed-Use | Building Width | 60 ft | needs_qualifier |  |
| Residential Accessory | Building Width | 30 ft | needs_qualifier |  |
| Commercial Accessory | Building Width | 30 ft | needs_qualifier |  |
| Residential | Building Depth | 50 ft | needs_qualifier |  |
| Mixed-Use | Building Depth | 50 ft | needs_qualifier |  |
| Residential Accessory | Building Depth | 40 ft | needs_qualifier |  |
| Commercial Accessory | Building Depth | 40 ft | needs_qualifier |  |
| Residential | Building Floor Area | - | not_established |  |
| Mixed-Use | Building Floor Area | - | not_established |  |
| Residential Accessory | Building Floor Area | - | not_established |  |
| Commercial Accessory | Building Floor Area | - | not_established |  |
| Residential | Total Stories | 2 | needs_qualifier |  |
| Mixed-Use | Total Stories | 2 | needs_qualifier |  |
| Residential Accessory | Total Stories | 1 | needs_qualifier |  |
| Commercial Accessory | Total Stories | 1 | needs_qualifier |  |
| Residential | First Floor Height | 12 ft | needs_qualifier |  |
| Mixed-Use | First Floor Height | 15 ft | needs_qualifier |  |
| Residential Accessory | First Floor Height | 16 ft | needs_qualifier |  |
| Commercial Accessory | First Floor Height | 16 ft | needs_qualifier |  |
| Residential | Upper Floor Height | 10 ft | needs_qualifier |  |
| Mixed-Use | Upper Floor Height | 10 ft | needs_qualifier |  |
| Residential Accessory | Upper Floor Height | 8 ft | needs_qualifier |  |
| Commercial Accessory | Upper Floor Height | 8 ft | needs_qualifier |  |
| Residential | Number of Units | - | not_established |  |
| Mixed-Use | Number of Units | - | not_established |  |
| Residential Accessory | Number of Units | 1 | needs_qualifier |  |
| Commercial Accessory | Number of Units | 1 | needs_qualifier |  |

### D4 - Village Residential

| Building | Field | Raw | Status | Bounds |
|---|---|---|---|---|
|  | Width | 50 ft min, 150 ft max | checkable | at least 50 ft, at most 150 ft |
|  | Depth | n/a | not_established |  |
|  | Lot Area | n/a | not_established |  |
|  | Primary Front Setback | 14 ft min, 35 ft max | checkable | at least 14 ft, at most 35 ft |
|  | Secondary Front Setback | 14 ft min | checkable | at least 14 ft |
|  | Side Setback | 8 ft min | checkable | at least 8 ft |
|  | Rear Setback | 8 ft min | checkable | at least 8 ft |
|  | Frontage Zone Setback | 4 ft min | checkable | at least 4 ft |
|  | Primary Front Setback | 14 ft min | checkable | at least 14 ft |
|  | Secondary Front Setback | 14 ft min | checkable | at least 14 ft |
|  | Side Setback | 8 ft min | checkable | at least 8 ft |
|  | Rear Setback | 8 ft min | checkable | at least 8 ft |
| Residential | Permitting Authority | Planning Board | not_a_number |  |
| Residential Accessory | Permitting Authority | CEO | not_a_number |  |
| Residential | Building Width | 60 ft | needs_qualifier |  |
| Residential Accessory | Building Width | 30 ft | needs_qualifier |  |
| Residential | Building Depth | 50 ft | needs_qualifier |  |
| Residential Accessory | Building Depth | 40 ft | needs_qualifier |  |
| Residential | Building Floor Area | 8,000 sf | needs_qualifier |  |
| Residential Accessory | Building Floor Area | - | not_established |  |
| Residential | Total Stories | 2 | needs_qualifier |  |
| Residential Accessory | Total Stories | 1 | needs_qualifier |  |
| Residential | First Floor Height | 12 ft | needs_qualifier |  |
| Residential Accessory | First Floor Height | 16 ft | needs_qualifier |  |
| Residential | Upper Floor Height | 10 ft | needs_qualifier |  |
| Residential Accessory | Upper Floor Height | 8 ft | needs_qualifier |  |
| Residential | Number of Units | - | not_established |  |
| Residential Accessory | Number of Units | 1 | needs_qualifier |  |

### D5 - Village Business

| Building | Field | Raw | Status | Bounds |
|---|---|---|---|---|
|  | Width | 20 ft min, 100 ft max | checkable | at least 20 ft, at most 100 ft |
|  | Depth | n/a | not_established |  |
|  | Lot Area | n/a | not_established |  |
|  | Primary Front Setback | 0 ft min, 20 ft max | checkable | at least 0 ft, at most 20 ft |
|  | Secondary Front Setback | 0 ft min, 15 ft max | checkable | at least 0 ft, at most 15 ft |
|  | Side Setback | 0 ft min, 25 ft max | checkable | at least 0 ft, at most 25 ft |
|  | Rear Setback | 5 ft min | checkable | at least 5 ft |
|  | Frontage Zone Setback | 20 ft min | checkable | at least 20 ft |
|  | Primary Front Setback | 20 ft min | checkable | at least 20 ft |
|  | Secondary Front Setback | 15 ft min | checkable | at least 15 ft |
|  | Side Setback | 15 ft min | checkable | at least 15 ft |
|  | Rear Setback | 5 ft min | checkable | at least 5 ft |
| Residential | Permitting Authority | CEO | not_a_number |  |
| Mixed-Use | Permitting Authority | CEO | not_a_number |  |
| Multi-Unit Commercial | Permitting Authority | Planning Board | not_a_number |  |
| Residential Accessory | Permitting Authority | CEO | not_a_number |  |
| Commercial Accessory | Permitting Authority | Planning Board | not_a_number |  |
| Residential | Building Width | 60 ft | needs_qualifier |  |
| Mixed-Use | Building Width | 60 ft | needs_qualifier |  |
| Multi-Unit Commercial | Building Width | 80 ft | needs_qualifier |  |
| Residential Accessory | Building Width | 30 ft | needs_qualifier |  |
| Commercial Accessory | Building Width | 30 ft | needs_qualifier |  |
| Residential | Building Depth | 75 ft | needs_qualifier |  |
| Mixed-Use | Building Depth | - | not_established |  |
| Multi-Unit Commercial | Building Depth | - | not_established |  |
| Residential Accessory | Building Depth | 40 ft | needs_qualifier |  |
| Commercial Accessory | Building Depth | 30 ft | needs_qualifier |  |
| Residential | Building Floor Area | - | not_established |  |
| Mixed-Use | Building Floor Area | 12,000 | needs_unit |  |
| Multi-Unit Commercial | Building Floor Area | - | not_established |  |
| Residential Accessory | Building Floor Area | - | not_established |  |
| Commercial Accessory | Building Floor Area | - | not_established |  |
| Residential | Total Stories | 2 | needs_qualifier |  |
| Mixed-Use | Total Stories | 2 | needs_qualifier |  |
| Multi-Unit Commercial | Total Stories | 2 | needs_qualifier |  |
| Residential Accessory | Total Stories | 2 | needs_qualifier |  |
| Commercial Accessory | Total Stories | 1 | needs_qualifier |  |
| Residential | First Floor Height | 12 ft | needs_qualifier |  |
| Mixed-Use | First Floor Height | 15 ft | needs_qualifier |  |
| Multi-Unit Commercial | First Floor Height | 15 ft | needs_qualifier |  |
| Residential Accessory | First Floor Height | 10 ft | needs_qualifier |  |
| Commercial Accessory | First Floor Height | 16 ft | needs_qualifier |  |
| Residential | Upper Floor Height | 10 ft | needs_qualifier |  |
| Mixed-Use | Upper Floor Height | 10 ft | needs_qualifier |  |
| Multi-Unit Commercial | Upper Floor Height | 10 ft | needs_qualifier |  |
| Residential Accessory | Upper Floor Height | 10 ft | needs_qualifier |  |
| Commercial Accessory | Upper Floor Height | 8 ft | needs_qualifier |  |
| Residential | Number of Units | - | not_established |  |
| Mixed-Use | Number of Units | - | not_established |  |
| Multi-Unit Commercial | Number of Units | 5 | needs_qualifier |  |
| Residential Accessory | Number of Units | 1 | needs_qualifier |  |
| Commercial Accessory | Number of Units | 1 | needs_qualifier |  |

### D6 - Town Center

| Building | Field | Raw | Status | Bounds |
|---|---|---|---|---|
|  | Width | 20 ft min, 100 ft max | checkable | at least 20 ft, at most 100 ft |
|  | Depth | n/a | not_established |  |
|  | Lot Area | n/a | not_established |  |
|  | Primary Front Setback | 0 ft max | checkable | at most 0 ft |
|  | Secondary Front Setback | 0 ft max | checkable | at most 0 ft |
|  | Side Setback | 0 ft min (4) , 5 ft max (5) | unresolved |  |
|  | Rear Setback | 5 ft min | checkable | at least 5 ft |
|  | Frontage Zone Setback | 20 ft min | checkable | at least 20 ft |
|  | Primary Front Setback | 25 ft min | checkable | at least 25 ft |
|  | Secondary Front Setback | 25 ft min | checkable | at least 25 ft |
|  | Side Setback | 0 ft min | checkable | at least 0 ft |
|  | Rear Setback | 5 ft min | checkable | at least 5 ft |
| Residential | Permitting Authority | Planning Board | not_a_number |  |
| Mixed-Use | Permitting Authority | Planning Board | not_a_number |  |
| Multi-Unit Commercial | Permitting Authority | Planning Board | not_a_number |  |
| Commercial Accessory | Permitting Authority | Planning Board | not_a_number |  |
| Residential | Building Width | 90 ft | needs_qualifier |  |
| Mixed-Use | Building Width | 90 ft | needs_qualifier |  |
| Multi-Unit Commercial | Building Width | 90 ft | needs_qualifier |  |
| Commercial Accessory | Building Width | 30 ft | needs_qualifier |  |
| Residential | Building Depth | 90 ft | needs_qualifier |  |
| Mixed-Use | Building Depth | 90 ft | needs_qualifier |  |
| Multi-Unit Commercial | Building Depth | 90 ft | needs_qualifier |  |
| Commercial Accessory | Building Depth | 40 ft | needs_qualifier |  |
| Residential | Building Floor Area | - | not_established |  |
| Mixed-Use | Building Floor Area | - | not_established |  |
| Multi-Unit Commercial | Building Floor Area | 18,000 sf | needs_qualifier |  |
| Commercial Accessory | Building Floor Area | - | not_established |  |
| Residential | Total Stories | 2 min. - 3 max. | checkable | at least 2 stories, at most 3 stories |
| Mixed-Use | Total Stories | 2 min. - 3 max. | checkable | at least 2 stories, at most 3 stories |
| Multi-Unit Commercial | Total Stories | 2 min. - 3 max. | checkable | at least 2 stories, at most 3 stories |
| Commercial Accessory | Total Stories | 1 max. | checkable | at most 1 stories |
| Residential | First Floor Height | 12 ft | needs_qualifier |  |
| Mixed-Use | First Floor Height | 15 ft | needs_qualifier |  |
| Multi-Unit Commercial | First Floor Height | 15 ft | needs_qualifier |  |
| Commercial Accessory | First Floor Height | 15 ft | needs_qualifier |  |
| Residential | Upper Floor Height | 10 ft | needs_qualifier |  |
| Mixed-Use | Upper Floor Height | 10 ft | needs_qualifier |  |
| Multi-Unit Commercial | Upper Floor Height | 10 ft | needs_qualifier |  |
| Commercial Accessory | Upper Floor Height | 8 ft | needs_qualifier |  |
| Residential | Number of Units | - | not_established |  |
| Mixed-Use | Number of Units | - | not_established |  |
| Multi-Unit Commercial | Number of Units | 20 | needs_qualifier |  |
| Commercial Accessory | Number of Units | 1 | needs_qualifier |  |

### SD - Historic

| Building | Field | Raw | Status | Bounds |
|---|---|---|---|---|
|  | Width | 50 ft min, 150 ft max | checkable | at least 50 ft, at most 150 ft |
|  | Depth | n/a | not_established |  |
|  | Lot Area | n/a | not_established |  |
|  | Primary Front Setback | 14 ft min, 35 ft max | checkable | at least 14 ft, at most 35 ft |
|  | Secondary Front Setback | 4 ft min | checkable | at least 4 ft |
|  | Side Setback | 8 ft min | checkable | at least 8 ft |
|  | Rear Setback | 8 ft min | checkable | at least 8 ft |
|  | Frontage Zone Setback | 20 ft | checkable | at least 20 ft |
|  | Primary Front Setback | 14 ft min | checkable | at least 14 ft |
|  | Secondary Front Setback | 4 ft min | checkable | at least 4 ft |
|  | Side Setback | 8 ft min | checkable | at least 8 ft |
|  | Rear Setback | 8 ft min | checkable | at least 8 ft |
| Residential | Permitting Authority | Planning Board | not_a_number |  |
| Residential Accessory | Permitting Authority | CEO | not_a_number |  |
| Residential | Building Width | 75 ft | needs_qualifier |  |
| Residential Accessory | Building Width | 30 ft | needs_qualifier |  |
| Residential | Building Depth | 50 ft | needs_qualifier |  |
| Residential Accessory | Building Depth | 40 ft | needs_qualifier |  |
| Residential | Building Floor Area | - | not_established |  |
| Residential Accessory | Building Floor Area | - | not_established |  |
| Residential | Total Stories | 2 | needs_qualifier |  |
| Residential Accessory | Total Stories | 1 | needs_qualifier |  |
| Residential | First Floor Height | 12 ft | needs_qualifier |  |
| Residential Accessory | First Floor Height | 16 ft | needs_qualifier |  |
| Residential | Upper Floor Height | 10 ft | needs_qualifier |  |
| Residential Accessory | Upper Floor Height | 8 ft | needs_qualifier |  |
| Residential | Number of Units | - | not_established |  |
| Residential Accessory | Number of Units | 1 | needs_qualifier |  |

### SD - Conservation

| Building | Field | Raw | Status | Bounds |
|---|---|---|---|---|
|  | Width | n/a | not_established |  |
|  | Depth | n/a | not_established |  |
|  | Lot Area | n/a | not_established |  |
|  | Primary Front Setback | n/a | not_established |  |
|  | Secondary Front Setback | n/a | not_established |  |
|  | Side Setback | n/a | not_established |  |
|  | Rear Setback | n/a | not_established |  |
|  | Frontage Zone Setback | n/a | not_established |  |
|  | Primary Front Setback | n/a | not_established |  |
|  | Secondary Front Setback | n/a | not_established |  |
|  | Side Setback | n/a | not_established |  |
|  | Rear Setback | n/a | not_established |  |

### SD - Highway Commercial

| Building | Field | Raw | Status | Bounds |
|---|---|---|---|---|
|  | Width | 50 ft min | checkable | at least 50 ft |
|  | Depth | n/a | not_established |  |
|  | Lot Area | n/a | not_established |  |
|  | Primary Front Setback | n/a | not_established |  |
|  | Secondary Front Setback | n/a | not_established |  |
|  | Side Setback | 5 ft min | checkable | at least 5 ft |
|  | Rear Setback | 5 ft min | checkable | at least 5 ft |
|  | Frontage Zone Setback | 20 ft min | checkable | at least 20 ft |
|  | Primary Front Setback | 50 ft min | checkable | at least 50 ft |
|  | Secondary Front Setback | 50 ft min | checkable | at least 50 ft |
|  | Side Setback | 5 ft min | checkable | at least 5 ft |
|  | Rear Setback | 5 ft min | checkable | at least 5 ft |
| Single Unit Commercial | Permitting Authority | Planning Board | not_a_number |  |
| Mixed-Use | Permitting Authority | Planning Board | not_a_number |  |
| Multi-Unit Commercial | Permitting Authority | Planning Board | not_a_number |  |
| Commercial Accessory | Permitting Authority | Planning Board | not_a_number |  |
| Residential Accessory | Permitting Authority | CEO | not_a_number |  |
| Single Unit Commercial | Building Width | 120 ft | needs_qualifier |  |
| Mixed-Use | Building Width | 120 ft | needs_qualifier |  |
| Multi-Unit Commercial | Building Width | 120 ft | needs_qualifier |  |
| Commercial Accessory | Building Width | 30 ft | needs_qualifier |  |
| Residential Accessory | Building Width | 30 ft | needs_qualifier |  |
| Single Unit Commercial | Building Depth | - | not_established |  |
| Mixed-Use | Building Depth | - | not_established |  |
| Multi-Unit Commercial | Building Depth | - | not_established |  |
| Commercial Accessory | Building Depth | 40 ft | needs_qualifier |  |
| Residential Accessory | Building Depth | 40 ft | needs_qualifier |  |
| Single Unit Commercial | Building Floor Area | 60,000 | needs_unit |  |
| Mixed-Use | Building Floor Area | 40,000 | needs_unit |  |
| Multi-Unit Commercial | Building Floor Area | 60,000 | needs_unit |  |
| Commercial Accessory | Building Floor Area | - | not_established |  |
| Residential Accessory | Building Floor Area | - | not_established |  |
| Single Unit Commercial | Total Stories | 3 | needs_qualifier |  |
| Mixed-Use | Total Stories | 3 | needs_qualifier |  |
| Multi-Unit Commercial | Total Stories | 3 | needs_qualifier |  |
| Commercial Accessory | Total Stories | 1 | needs_qualifier |  |
| Residential Accessory | Total Stories | 1 | needs_qualifier |  |
| Single Unit Commercial | First Floor Height | 12 ft | needs_qualifier |  |
| Mixed-Use | First Floor Height | 15 ft | needs_qualifier |  |
| Multi-Unit Commercial | First Floor Height | 15 ft | needs_qualifier |  |
| Commercial Accessory | First Floor Height | 15 ft | needs_qualifier |  |
| Residential Accessory | First Floor Height | 16 ft | needs_qualifier |  |
| Single Unit Commercial | Upper Floor Height | 10 ft | needs_qualifier |  |
| Mixed-Use | Upper Floor Height | 10 ft | needs_qualifier |  |
| Multi-Unit Commercial | Upper Floor Height | 10 ft | needs_qualifier |  |
| Commercial Accessory | Upper Floor Height | 10 ft | needs_qualifier |  |
| Residential Accessory | Upper Floor Height | 8 ft | needs_qualifier |  |
| Single Unit Commercial | Number of Units | 1 | needs_qualifier |  |
| Mixed-Use | Number of Units | - | not_established |  |
| Multi-Unit Commercial | Number of Units | - | not_established |  |
| Commercial Accessory | Number of Units | 1 | needs_qualifier |  |
| Residential Accessory | Number of Units | 1 | needs_qualifier |  |

### SD - Rural Highway

| Building | Field | Raw | Status | Bounds |
|---|---|---|---|---|
|  | Width | 1000 ft min (1) | unresolved |  |
|  | Depth | n/a | not_established |  |
|  | Lot Area | n/a | not_established |  |
|  | Primary Front Setback | 200 ft min | checkable | at least 200 ft |
|  | Secondary Front Setback | 50 ft min | checkable | at least 50 ft |
|  | Side Setback | 15 ft min | checkable | at least 15 ft |
|  | Rear Setback | 15 ft min | checkable | at least 15 ft |
|  | Frontage Zone Setback | 20 ft min | checkable | at least 20 ft |
|  | Primary Front Setback | 200 ft min | checkable | at least 200 ft |
|  | Secondary Front Setback | 50 ft min | checkable | at least 50 ft |
|  | Side Setback | 15 ft min | checkable | at least 15 ft |
|  | Rear Setback | 15 ft min | checkable | at least 15 ft |
| Single Unit Commercial | Permitting Authority | Planning Board | not_a_number |  |
| Mixed-Use | Permitting Authority | Planning Board | not_a_number |  |
| Multi-Unit Commercial | Permitting Authority | Planning Board | not_a_number |  |
| Commercial Accessory | Permitting Authority | Planning Board | not_a_number |  |
| Residential Accessory | Permitting Authority | CEO | not_a_number |  |
| Single Unit Commercial | Building Width | 120 ft | needs_qualifier |  |
| Mixed-Use | Building Width | 120 ft | needs_qualifier |  |
| Multi-Unit Commercial | Building Width | 120 ft | needs_qualifier |  |
| Commercial Accessory | Building Width | 30 ft | needs_qualifier |  |
| Residential Accessory | Building Width | 30 ft | needs_qualifier |  |
| Single Unit Commercial | Building Depth | - | not_established |  |
| Mixed-Use | Building Depth | - | not_established |  |
| Multi-Unit Commercial | Building Depth | - | not_established |  |
| Commercial Accessory | Building Depth | 40 ft | needs_qualifier |  |
| Residential Accessory | Building Depth | 40 ft | needs_qualifier |  |
| Single Unit Commercial | Building Floor Area | 60,000 sf | needs_qualifier |  |
| Mixed-Use | Building Floor Area | 40,000 sf | needs_qualifier |  |
| Multi-Unit Commercial | Building Floor Area | 60,000 sf | needs_qualifier |  |
| Commercial Accessory | Building Floor Area | - | not_established |  |
| Residential Accessory | Building Floor Area | - | not_established |  |
| Single Unit Commercial | Total Stories | 3 | needs_qualifier |  |
| Mixed-Use | Total Stories | 3 | needs_qualifier |  |
| Multi-Unit Commercial | Total Stories | 3 | needs_qualifier |  |
| Commercial Accessory | Total Stories | 1 | needs_qualifier |  |
| Residential Accessory | Total Stories | 1 | needs_qualifier |  |
| Single Unit Commercial | First Floor Height | 12 ft | needs_qualifier |  |
| Mixed-Use | First Floor Height | 15 ft | needs_qualifier |  |
| Multi-Unit Commercial | First Floor Height | 15 ft | needs_qualifier |  |
| Commercial Accessory | First Floor Height | 15 ft | needs_qualifier |  |
| Residential Accessory | First Floor Height | 16 ft | needs_qualifier |  |
| Single Unit Commercial | Upper Floor Height | 10 ft | needs_qualifier |  |
| Mixed-Use | Upper Floor Height | 10 ft | needs_qualifier |  |
| Multi-Unit Commercial | Upper Floor Height | 10 ft | needs_qualifier |  |
| Commercial Accessory | Upper Floor Height | 10 ft | needs_qualifier |  |
| Residential Accessory | Upper Floor Height | 8 ft | needs_qualifier |  |
| Single Unit Commercial | Number of Units | 1 | needs_qualifier |  |
| Mixed-Use | Number of Units | - | not_established |  |
| Multi-Unit Commercial | Number of Units | 20 | needs_qualifier |  |
| Commercial Accessory | Number of Units | 1 | needs_qualifier |  |
| Residential Accessory | Number of Units | 1 | needs_qualifier |  |

### SD - Campus

| Building | Field | Raw | Status | Bounds |
|---|---|---|---|---|
|  | Width | 100 ft min | checkable | at least 100 ft |
|  | Depth | n/a | not_established |  |
|  | Lot Area | n/a | not_established |  |
|  | Primary Front Setback | 0 ft min | checkable | at least 0 ft |
|  | Secondary Front Setback | 0 ft min | checkable | at least 0 ft |
|  | Side Setback | 5 ft min | checkable | at least 5 ft |
|  | Rear Setback | 5 ft min | checkable | at least 5 ft |
|  | Frontage Zone Setback | 20 ft min | checkable | at least 20 ft |

### SD - Marine

| Building | Field | Raw | Status | Bounds |
|---|---|---|---|---|
|  | Width | 100 ft min | checkable | at least 100 ft |
|  | Depth | n/a | not_established |  |
|  | Lot Area | n/a | not_established |  |
|  | Primary Front Setback | 14 ft min, 35 ft max | checkable | at least 14 ft, at most 35 ft |
|  | Secondary Front Setback | 4 ft min | checkable | at least 4 ft |
|  | Side Setback | 8 ft min | checkable | at least 8 ft |
|  | Rear Setback | 8 ft min | checkable | at least 8 ft |
|  | Frontage Zone Setback | 20 ft | checkable | at least 20 ft |

### SD - Fabrication

| Building | Field | Raw | Status | Bounds |
|---|---|---|---|---|
|  | Width | 20 ft min, 100 ft max | checkable | at least 20 ft, at most 100 ft |
|  | Depth | n/a | not_established |  |
|  | Lot Area | n/a | not_established |  |
|  | Primary Front Setback | 0 ft min, 20 ft max | checkable | at least 0 ft, at most 20 ft |
|  | Secondary Front Setback | 0 ft min, 20 ft max | checkable | at least 0 ft, at most 20 ft |
|  | Side Setback | 5 ft min | checkable | at least 5 ft |
|  | Rear Setback | 5 ft min | checkable | at least 5 ft |
|  | Frontage Zone Setback | 4 ft min | checkable | at least 4 ft |
|  | Primary Front Setback | 20 ft min | checkable | at least 20 ft |
|  | Secondary Front Setback | 3 ft min | checkable | at least 3 ft |
|  | Side Setback | 5 ft min | checkable | at least 5 ft |
|  | Rear Setback | 5 ft min | checkable | at least 5 ft |
| Single Unit Commercial | Permitting Authority | Planning Board | not_a_number |  |
| Mixed-Use | Permitting Authority | Planning Board | not_a_number |  |
| Multi-Unit Commercial | Permitting Authority | Planning Board | not_a_number |  |
| Commercial Accessory | Permitting Authority | Planning Board | not_a_number |  |
| Residential Accessory | Permitting Authority | CEO | not_a_number |  |
| Single Unit Commercial | Building Width | 120 ft | needs_qualifier |  |
| Mixed-Use | Building Width | 150 ft | needs_qualifier |  |
| Multi-Unit Commercial | Building Width | 120 ft | needs_qualifier |  |
| Commercial Accessory | Building Width | 30 ft | needs_qualifier |  |
| Residential Accessory | Building Width | 30 ft | needs_qualifier |  |
| Single Unit Commercial | Building Depth | - | not_established |  |
| Mixed-Use | Building Depth | - | not_established |  |
| Multi-Unit Commercial | Building Depth | - | not_established |  |
| Commercial Accessory | Building Depth | 40 ft | needs_qualifier |  |
| Residential Accessory | Building Depth | 40 ft | needs_qualifier |  |
| Single Unit Commercial | Building Floor Area | 50,000 | needs_unit |  |
| Mixed-Use | Building Floor Area | 60,000 | needs_unit |  |
| Multi-Unit Commercial | Building Floor Area | 50,000 | needs_unit |  |
| Commercial Accessory | Building Floor Area | - | not_established |  |
| Residential Accessory | Building Floor Area | - | not_established |  |
| Single Unit Commercial | Total Stories | 2 | needs_qualifier |  |
| Mixed-Use | Total Stories | 2 | needs_qualifier |  |
| Multi-Unit Commercial | Total Stories | 2 | needs_qualifier |  |
| Commercial Accessory | Total Stories | 1 | needs_qualifier |  |
| Residential Accessory | Total Stories | 1 | needs_qualifier |  |
| Single Unit Commercial | First Floor Height | 22 ft | needs_qualifier |  |
| Mixed-Use | First Floor Height | 22 ft | needs_qualifier |  |
| Multi-Unit Commercial | First Floor Height | 22 ft | needs_qualifier |  |
| Commercial Accessory | First Floor Height | 22 ft | needs_qualifier |  |
| Residential Accessory | First Floor Height | 16 ft | needs_qualifier |  |
| Single Unit Commercial | Upper Floor Height | 10 ft | needs_qualifier |  |
| Mixed-Use | Upper Floor Height | 10 ft | needs_qualifier |  |
| Multi-Unit Commercial | Upper Floor Height | 10 ft | needs_qualifier |  |
| Commercial Accessory | Upper Floor Height | 10 ft | needs_qualifier |  |
| Residential Accessory | Upper Floor Height | 8 ft | needs_qualifier |  |
| Single Unit Commercial | Number of Units | 1 | needs_qualifier |  |
| Mixed-Use | Number of Units | - | not_established |  |
| Multi-Unit Commercial | Number of Units | - | not_established |  |
| Commercial Accessory | Number of Units | 1 | needs_qualifier |  |
| Residential Accessory | Number of Units | 1 | needs_qualifier |  |

## 3. Questions only the chair can answer

The Code gives these numbers without a minimum or maximum, without a unit, or with a footnote whose text is missing. Until the chair answers, the builder can't check them and never treats them as a "no".

Article 5 says what the Permitted Buildings dimensions apply to:

> The standards set forth in the Permitted Building tables under Article 2 - District Standards for Building Width, Building Depth, and Total Square Feet apply only to the Main Building Mass of Primary Buildings and Accessory Buildings.

**Q1. Is Building Width in the Permitted Buildings tables a maximum?** If not, is it a minimum?

- D1 - Rural, Residential: 50 ft
- D1 - Rural, General Accessory: 30 ft
- D2 - Neighborhood Residential, Residential: 75 ft
- D2 - Neighborhood Residential, Mixed-Use: 50 ft
- D2 - Neighborhood Residential, Residential Accessory: 30 ft
- D3 - Neighborhood Business, Residential: 50 ft
- D3 - Neighborhood Business, Mixed-Use: 60 ft
- D3 - Neighborhood Business, Residential Accessory: 30 ft
- D3 - Neighborhood Business, Commercial Accessory: 30 ft
- D4 - Village Residential, Residential: 60 ft
- D4 - Village Residential, Residential Accessory: 30 ft
- D5 - Village Business, Residential: 60 ft
- D5 - Village Business, Mixed-Use: 60 ft
- D5 - Village Business, Multi-Unit Commercial: 80 ft
- D5 - Village Business, Residential Accessory: 30 ft
- D5 - Village Business, Commercial Accessory: 30 ft
- D6 - Town Center, Residential: 90 ft
- D6 - Town Center, Mixed-Use: 90 ft
- D6 - Town Center, Multi-Unit Commercial: 90 ft
- D6 - Town Center, Commercial Accessory: 30 ft
- SD - Historic, Residential: 75 ft
- SD - Historic, Residential Accessory: 30 ft
- SD - Highway Commercial, Single Unit Commercial: 120 ft
- SD - Highway Commercial, Mixed-Use: 120 ft
- SD - Highway Commercial, Multi-Unit Commercial: 120 ft
- SD - Highway Commercial, Commercial Accessory: 30 ft
- SD - Highway Commercial, Residential Accessory: 30 ft
- SD - Rural Highway, Single Unit Commercial: 120 ft
- SD - Rural Highway, Mixed-Use: 120 ft
- SD - Rural Highway, Multi-Unit Commercial: 120 ft
- SD - Rural Highway, Commercial Accessory: 30 ft
- SD - Rural Highway, Residential Accessory: 30 ft
- SD - Fabrication, Single Unit Commercial: 120 ft
- SD - Fabrication, Mixed-Use: 150 ft
- SD - Fabrication, Multi-Unit Commercial: 120 ft
- SD - Fabrication, Commercial Accessory: 30 ft
- SD - Fabrication, Residential Accessory: 30 ft

**Q2. Is Building Depth in the Permitted Buildings tables a maximum?** If not, is it a minimum?

- D1 - Rural, Residential: 50 ft
- D1 - Rural, General Accessory: 40 ft
- D2 - Neighborhood Residential, Residential: 50 ft
- D2 - Neighborhood Residential, Mixed-Use: 50 ft
- D2 - Neighborhood Residential, Residential Accessory: 40 ft
- D3 - Neighborhood Business, Residential: 50 ft
- D3 - Neighborhood Business, Mixed-Use: 50 ft
- D3 - Neighborhood Business, Residential Accessory: 40 ft
- D3 - Neighborhood Business, Commercial Accessory: 40 ft
- D4 - Village Residential, Residential: 50 ft
- D4 - Village Residential, Residential Accessory: 40 ft
- D5 - Village Business, Residential: 75 ft
- D5 - Village Business, Residential Accessory: 40 ft
- D5 - Village Business, Commercial Accessory: 30 ft
- D6 - Town Center, Residential: 90 ft
- D6 - Town Center, Mixed-Use: 90 ft
- D6 - Town Center, Multi-Unit Commercial: 90 ft
- D6 - Town Center, Commercial Accessory: 40 ft
- SD - Historic, Residential: 50 ft
- SD - Historic, Residential Accessory: 40 ft
- SD - Highway Commercial, Commercial Accessory: 40 ft
- SD - Highway Commercial, Residential Accessory: 40 ft
- SD - Rural Highway, Commercial Accessory: 40 ft
- SD - Rural Highway, Residential Accessory: 40 ft
- SD - Fabrication, Commercial Accessory: 40 ft
- SD - Fabrication, Residential Accessory: 40 ft

**Q3. Is Total Stories in the Permitted Buildings tables a maximum?** If not, is it a minimum?

- D1 - Rural, Residential: 2
- D1 - Rural, General Accessory: 1
- D2 - Neighborhood Residential, Residential: 2
- D2 - Neighborhood Residential, Mixed-Use: 2
- D2 - Neighborhood Residential, Residential Accessory: 1
- D3 - Neighborhood Business, Residential: 2
- D3 - Neighborhood Business, Mixed-Use: 2
- D3 - Neighborhood Business, Residential Accessory: 1
- D3 - Neighborhood Business, Commercial Accessory: 1
- D4 - Village Residential, Residential: 2
- D4 - Village Residential, Residential Accessory: 1
- D5 - Village Business, Residential: 2
- D5 - Village Business, Mixed-Use: 2
- D5 - Village Business, Multi-Unit Commercial: 2
- D5 - Village Business, Residential Accessory: 2
- D5 - Village Business, Commercial Accessory: 1
- SD - Historic, Residential: 2
- SD - Historic, Residential Accessory: 1
- SD - Highway Commercial, Single Unit Commercial: 3
- SD - Highway Commercial, Mixed-Use: 3
- SD - Highway Commercial, Multi-Unit Commercial: 3
- SD - Highway Commercial, Commercial Accessory: 1
- SD - Highway Commercial, Residential Accessory: 1
- SD - Rural Highway, Single Unit Commercial: 3
- SD - Rural Highway, Mixed-Use: 3
- SD - Rural Highway, Multi-Unit Commercial: 3
- SD - Rural Highway, Commercial Accessory: 1
- SD - Rural Highway, Residential Accessory: 1
- SD - Fabrication, Single Unit Commercial: 2
- SD - Fabrication, Mixed-Use: 2
- SD - Fabrication, Multi-Unit Commercial: 2
- SD - Fabrication, Commercial Accessory: 1
- SD - Fabrication, Residential Accessory: 1

**Q4. Is First Floor Height in the Permitted Buildings tables a maximum?** If not, is it a minimum?

- D1 - Rural, Residential: 12 ft
- D1 - Rural, General Accessory: 16 ft
- D2 - Neighborhood Residential, Residential: 12 ft
- D2 - Neighborhood Residential, Mixed-Use: 12 ft
- D2 - Neighborhood Residential, Residential Accessory: 16 ft
- D3 - Neighborhood Business, Residential: 12 ft
- D3 - Neighborhood Business, Mixed-Use: 15 ft
- D3 - Neighborhood Business, Residential Accessory: 16 ft
- D3 - Neighborhood Business, Commercial Accessory: 16 ft
- D4 - Village Residential, Residential: 12 ft
- D4 - Village Residential, Residential Accessory: 16 ft
- D5 - Village Business, Residential: 12 ft
- D5 - Village Business, Mixed-Use: 15 ft
- D5 - Village Business, Multi-Unit Commercial: 15 ft
- D5 - Village Business, Residential Accessory: 10 ft
- D5 - Village Business, Commercial Accessory: 16 ft
- D6 - Town Center, Residential: 12 ft
- D6 - Town Center, Mixed-Use: 15 ft
- D6 - Town Center, Multi-Unit Commercial: 15 ft
- D6 - Town Center, Commercial Accessory: 15 ft
- SD - Historic, Residential: 12 ft
- SD - Historic, Residential Accessory: 16 ft
- SD - Highway Commercial, Single Unit Commercial: 12 ft
- SD - Highway Commercial, Mixed-Use: 15 ft
- SD - Highway Commercial, Multi-Unit Commercial: 15 ft
- SD - Highway Commercial, Commercial Accessory: 15 ft
- SD - Highway Commercial, Residential Accessory: 16 ft
- SD - Rural Highway, Single Unit Commercial: 12 ft
- SD - Rural Highway, Mixed-Use: 15 ft
- SD - Rural Highway, Multi-Unit Commercial: 15 ft
- SD - Rural Highway, Commercial Accessory: 15 ft
- SD - Rural Highway, Residential Accessory: 16 ft
- SD - Fabrication, Single Unit Commercial: 22 ft
- SD - Fabrication, Mixed-Use: 22 ft
- SD - Fabrication, Multi-Unit Commercial: 22 ft
- SD - Fabrication, Commercial Accessory: 22 ft
- SD - Fabrication, Residential Accessory: 16 ft

**Q5. Is Upper Floor Height in the Permitted Buildings tables a maximum?** If not, is it a minimum?

- D1 - Rural, Residential: 10 ft
- D1 - Rural, General Accessory: 10 ft
- D2 - Neighborhood Residential, Residential: 10 ft
- D2 - Neighborhood Residential, Mixed-Use: 10 ft
- D2 - Neighborhood Residential, Residential Accessory: 8 ft
- D3 - Neighborhood Business, Residential: 10 ft
- D3 - Neighborhood Business, Mixed-Use: 10 ft
- D3 - Neighborhood Business, Residential Accessory: 8 ft
- D3 - Neighborhood Business, Commercial Accessory: 8 ft
- D4 - Village Residential, Residential: 10 ft
- D4 - Village Residential, Residential Accessory: 8 ft
- D5 - Village Business, Residential: 10 ft
- D5 - Village Business, Mixed-Use: 10 ft
- D5 - Village Business, Multi-Unit Commercial: 10 ft
- D5 - Village Business, Residential Accessory: 10 ft
- D5 - Village Business, Commercial Accessory: 8 ft
- D6 - Town Center, Residential: 10 ft
- D6 - Town Center, Mixed-Use: 10 ft
- D6 - Town Center, Multi-Unit Commercial: 10 ft
- D6 - Town Center, Commercial Accessory: 8 ft
- SD - Historic, Residential: 10 ft
- SD - Historic, Residential Accessory: 8 ft
- SD - Highway Commercial, Single Unit Commercial: 10 ft
- SD - Highway Commercial, Mixed-Use: 10 ft
- SD - Highway Commercial, Multi-Unit Commercial: 10 ft
- SD - Highway Commercial, Commercial Accessory: 10 ft
- SD - Highway Commercial, Residential Accessory: 8 ft
- SD - Rural Highway, Single Unit Commercial: 10 ft
- SD - Rural Highway, Mixed-Use: 10 ft
- SD - Rural Highway, Multi-Unit Commercial: 10 ft
- SD - Rural Highway, Commercial Accessory: 10 ft
- SD - Rural Highway, Residential Accessory: 8 ft
- SD - Fabrication, Single Unit Commercial: 10 ft
- SD - Fabrication, Mixed-Use: 10 ft
- SD - Fabrication, Multi-Unit Commercial: 10 ft
- SD - Fabrication, Commercial Accessory: 10 ft
- SD - Fabrication, Residential Accessory: 8 ft

**Q6. Is Number of Units in the Permitted Buildings tables a maximum?** If not, is it a minimum?

- D1 - Rural, General Accessory: 2
- D2 - Neighborhood Residential, Residential Accessory: 1
- D3 - Neighborhood Business, Residential Accessory: 1
- D3 - Neighborhood Business, Commercial Accessory: 1
- D4 - Village Residential, Residential Accessory: 1
- D5 - Village Business, Multi-Unit Commercial: 5
- D5 - Village Business, Residential Accessory: 1
- D5 - Village Business, Commercial Accessory: 1
- D6 - Town Center, Multi-Unit Commercial: 20
- D6 - Town Center, Commercial Accessory: 1
- SD - Historic, Residential Accessory: 1
- SD - Highway Commercial, Single Unit Commercial: 1
- SD - Highway Commercial, Commercial Accessory: 1
- SD - Highway Commercial, Residential Accessory: 1
- SD - Rural Highway, Single Unit Commercial: 1
- SD - Rural Highway, Multi-Unit Commercial: 20
- SD - Rural Highway, Commercial Accessory: 1
- SD - Rural Highway, Residential Accessory: 1
- SD - Fabrication, Single Unit Commercial: 1
- SD - Fabrication, Commercial Accessory: 1
- SD - Fabrication, Residential Accessory: 1

**Q7. Is Building Floor Area in the Permitted Buildings tables a maximum?** If not, is it a minimum?

- D4 - Village Residential, Residential: 8,000 sf
- D6 - Town Center, Multi-Unit Commercial: 18,000 sf
- SD - Rural Highway, Single Unit Commercial: 60,000 sf
- SD - Rural Highway, Mixed-Use: 40,000 sf
- SD - Rural Highway, Multi-Unit Commercial: 60,000 sf

**Q8. What unit is the Building Floor Area of 12,000 for Mixed-Use in D5 - Village Business?** The Code gives '12,000' for Building Floor Area without a unit.

**Q9. What unit is the Building Floor Area of 60,000 for Single Unit Commercial in SD - Highway Commercial?** The Code gives '60,000' for Building Floor Area without a unit.

**Q10. What unit is the Building Floor Area of 40,000 for Mixed-Use in SD - Highway Commercial?** The Code gives '40,000' for Building Floor Area without a unit.

**Q11. What unit is the Building Floor Area of 60,000 for Multi-Unit Commercial in SD - Highway Commercial?** The Code gives '60,000' for Building Floor Area without a unit.

**Q12. What unit is the Building Floor Area of 50,000 for Single Unit Commercial in SD - Fabrication?** The Code gives '50,000' for Building Floor Area without a unit.

**Q13. What unit is the Building Floor Area of 60,000 for Mixed-Use in SD - Fabrication?** The Code gives '60,000' for Building Floor Area without a unit.

**Q14. What unit is the Building Floor Area of 50,000 for Multi-Unit Commercial in SD - Fabrication?** The Code gives '50,000' for Building Floor Area without a unit.

**Q15. D6 - Town Center, Side Setback (0 ft min (4) , 5 ft max (5)).** Footnote text for (4), (5) is not present in the Article 2 extract (source/article-02-data.json). See DECISIONS-NEEDED.md.

**Q16. SD - Rural Highway, Width (1000 ft min (1)).** Footnote text for (1) is not present in the Article 2 extract (source/article-02-data.json). See DECISIONS-NEEDED.md.

**Q17. SD - Conservation has no Permitted Buildings table.** Article 2 establishes no building dimensional standards for the SD - Conservation District. What dimensional standards, if any, does the Board apply to this proposal?

**Q18. SD - Campus has no Permitted Buildings table.** Article 2 establishes no building dimensional standards for the SD - Campus District. What dimensional standards, if any, does the Board apply to this proposal?

**Q19. SD - Marine has no Permitted Buildings table.** Article 2 establishes no building dimensional standards for the SD - Marine District. What dimensional standards, if any, does the Board apply to this proposal?

## 4. What the Code says in prose, not yet checkable

These sections are written as sentences, not as numbers in a table. Each needs either a rule the builder can check or an approved plain-language entry in the explanation library. This is the work list later plans are sized from.

| Article | Section | Name | Provisions | Status |
|---|---|---|---|---|
| 1 (General Standards) | 1 | Core Zoning Code | 21 | prose — needs a rule or a library entry |
| 1 (General Standards) | 2 | Code Instructions | 14 | prose — needs a rule or a library entry |
| 1 (General Standards) | 3 | District Map | 6 | prose — needs a rule or a library entry |
| 1 (General Standards) | 4 | Authority & Compliance | 10 | prose — needs a rule or a library entry |
| 1 (General Standards) | 5 | Adoption & Effect | 4 | prose — needs a rule or a library entry |
| 3 (Thoroughfares) | 1 | General | 21 | prose — needs a rule or a library entry |
| 3 (Thoroughfares) | 2 | Thoroughfare Types | 15 | prose — needs a rule or a library entry |
| 3 (Thoroughfares) | 3 | Thoroughfare Standards | 42 | prose — needs a rule or a library entry |
| 3 (Thoroughfares) | 4 | Ownership Categories | 13 | prose — needs a rule or a library entry |
| 3 (Thoroughfares) | 5 | Classification Of Existing Thoroughfares | 35 | prose — needs a rule or a library entry |
| 3 (Thoroughfares) | 6 | New Thoroughfares | 36 | prose — needs a rule or a library entry |
| 3 (Thoroughfares) | 7 | Driveways | 28 | prose — needs a rule or a library entry |
| 3 (Thoroughfares) | 8 | Entrances | 22 | prose — needs a rule or a library entry |
| 3 (Thoroughfares) | 9 | Intersections | 9 | prose — needs a rule or a library entry |
| 3 (Thoroughfares) | 10 | Water Management | 11 | prose — needs a rule or a library entry |
| 3 (Thoroughfares) | 11 | Construction Standards | 8 | prose — needs a rule or a library entry |
| 3 (Thoroughfares) | 12 | Coordination With Maine Dot | 10 | prose — needs a rule or a library entry |
| 3 (Thoroughfares) | 13 | Administration | 21 | prose — needs a rule or a library entry |
| 3 (Thoroughfares) | 14 | Nonconforming Thoroughfares | 14 | prose — needs a rule or a library entry |
| 4 (Site Standards) | 1 | Site Standards | 3 | prose — needs a rule or a library entry |
| 4 (Site Standards) | 2 | Driveways | 3 | prose — needs a rule or a library entry |
| 4 (Site Standards) | 3 | Vehicular Parking | 39 | prose — needs a rule or a library entry |
| 4 (Site Standards) | 4 | Bicycle Parking | 13 | prose — needs a rule or a library entry |
| 4 (Site Standards) | 5 | Natural Screening | 30 | prose — needs a rule or a library entry |
| 4 (Site Standards) | 6 | Landscaping | 13 | prose — needs a rule or a library entry |
| 4 (Site Standards) | 7 | Fields | 7 | prose — needs a rule or a library entry |
| 4 (Site Standards) | 8 | Fences & Walls | 19 | prose — needs a rule or a library entry |
| 4 (Site Standards) | 9 | Mechanical Equipment | 7 | prose — needs a rule or a library entry |
| 4 (Site Standards) | 10 | Loading Docks | 8 | prose — needs a rule or a library entry |
| 4 (Site Standards) | 11 | Drive-Throughs | 10 | prose — needs a rule or a library entry |
| 4 (Site Standards) | 12 | Lighting | 60 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 1 | Building Types | 16 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 2 | Number Of Buildings | 10 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 3 | Building Assembly | 19 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 4 | Building Elevation | 9 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 5 | Additions | 11 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 6 | Building Articulation | 15 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 7 | Height | 11 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 8 | Materials | 6 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 9 | Additional Structures | 17 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 10 | Temporary Structures | 7 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 11 | Primary Entrances | 10 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 12 | Shopfronts | 12 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 13 | Slopes & Terraces | 16 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 14 | Mezzanines | 12 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 15 | Nonconforming Buildings | 14 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 16 | Large Scale Buildings | 8 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 17 | Size Cap | 3 | prose — needs a rule or a library entry |
| 5 (Building Standards) | 18 | Building Groups | 93 | prose — needs a rule or a library entry |
| 6 (Design Standards) | 1 | General | 9 | prose — needs a rule or a library entry |
| 6 (Design Standards) | 2 | Components, General | 23 | prose — needs a rule or a library entry |
| 6 (Design Standards) | 3 | Massing Components | 45 | prose — needs a rule or a library entry |
| 6 (Design Standards) | 4 | Architectural Components | 128 | prose — needs a rule or a library entry |
| 6 (Design Standards) | 5 | Roofs | 13 | prose — needs a rule or a library entry |
| 6 (Design Standards) | 6 | Window & Door | 17 | prose — needs a rule or a library entry |
| 6 (Design Standards) | 7 | Building Orientation | 5 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 1 | Use Standards | 32 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 2 | Expanded Use Standards | 5 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 3 | Adult Establishment | 7 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 4 | Amusement, Indoor | 1 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 5 | Amusement, Outdoor | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 6 | Animal Care, Indoor | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 7 | Animal Care, Outdoor | 7 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 8 | Aquaculture | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 9 | Assembly | 3 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 10 | Banking & Financial Services | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 11 | Bar Or Tavern | 7 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 12 | Bed & Breakfast | 4 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 13 | Campground | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 14 | Car Wash | 1 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 15 | College/University | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 16 | Commercial Agriculture | 3 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 17 | Commercial School | 1 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 18 | Cultural Facility | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 19 | Day Care Center | 3 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 20 | Day Care Facility | 3 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 21 | Dispatch Service | 4 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 22 | District Energy System | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 23 | Dormitory | 1 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 24 | Drive-Through Facility | 1 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 25 | Farm/Vendor Market | 4 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 26 | Farmstand | 1 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 27 | Food Pantry | 3 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 28 | Funeral Services | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 29 | Gas Station | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 30 | Health Care Provider | 1 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 31 | Health/Fitness Studio | 1 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 32 | Hospital | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 33 | Hotel & Hostel | 4 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 34 | Human Service Facility | 3 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 35 | Industrial, Artisan | 3 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 36 | Industrial, General | 3 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 37 | Industrial, Heavy | 4 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 38 | Junk/Salvage Yard | 5 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 39 | Live Entertainment | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 40 | Marina, Dry Storage | 1 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 41 | Marina, Recreation | 3 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 42 | Mobile Home Park | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 43 | Office, Large | 1 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 44 | Office, Medium | 1 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 45 | Office, Small | 1 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 46 | Outdoor Storage | 4 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 47 | Packaged Liquor | 1 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 48 | Parking Lot | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 49 | Primary/Secondary School | 1 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 50 | Private Club Or Lodge | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 51 | Recycling Facility | 4 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 52 | Research Laboratory | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 53 | Residence | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 54 | Residential Care Facility | 1 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 55 | Resource Extraction | 7 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 56 | Restaurant & Cafe | 8 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 57 | Retail & Service, General | 1 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 58 | Retail & Service, Heavy | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 59 | Retail Firearm Sales Facility | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 60 | Rooming House | 3 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 61 | Self-Storage Facility | 5 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 62 | Stables / Riding Center | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 63 | Tourist Rental | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 64 | Utilities & Services | 10 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 65 | Vehicle Rental Or Sales | 2 | prose — needs a rule or a library entry |
| 7 (Use Standards) | 66 | Vehicle Repair | 6 | prose — needs a rule or a library entry |
| 8 (Administration) | 1 | Core Code Administration | 4 | prose — needs a rule or a library entry |
| 8 (Administration) | 2 | General Procedures | 17 | prose — needs a rule or a library entry |
| 8 (Administration) | 3 | Pre-Submittal Meeting | 11 | prose — needs a rule or a library entry |
| 8 (Administration) | 4 | Optional Neighborhood Meeting | 18 | prose — needs a rule or a library entry |
| 8 (Administration) | 5 | Public Notice | 12 | prose — needs a rule or a library entry |
| 8 (Administration) | 6 | Public Hearings | 9 | prose — needs a rule or a library entry |
| 8 (Administration) | 7 | Written Interpretation | 11 | prose — needs a rule or a library entry |
| 8 (Administration) | 8 | Misc Procedures | 17 | prose — needs a rule or a library entry |
| 8 (Administration) | 9 | Application Types | 23 | prose — needs a rule or a library entry |
| 8 (Administration) | 10 | Small Project Plan | 26 | prose — needs a rule or a library entry |
| 8 (Administration) | 11 | Large Project Plan | 32 | prose — needs a rule or a library entry |
| 8 (Administration) | 12 | Subdivision | 82 | prose — needs a rule or a library entry |
| 8 (Administration) | 13 | Master Plan | 22 | prose — needs a rule or a library entry |
| 8 (Administration) | 14 | Plan Revision | 13 | prose — needs a rule or a library entry |
| 8 (Administration) | 15 | Use Permit | 8 | prose — needs a rule or a library entry |
| 8 (Administration) | 16 | Expanded Use Permit | 3 | prose — needs a rule or a library entry |
| 8 (Administration) | 17 | Residential Companion Use Permit | 3 | prose — needs a rule or a library entry |
| 8 (Administration) | 18 | Special Permit | 23 | prose — needs a rule or a library entry |
| 8 (Administration) | 19 | Variance | 35 | prose — needs a rule or a library entry |
| 8 (Administration) | 20 | Land Conveyance | 13 | prose — needs a rule or a library entry |
| 8 (Administration) | 21 | Zoning Amendment | 17 | prose — needs a rule or a library entry |
| 8 (Administration) | 22 | Demolition Of Historic Assets | 21 | prose — needs a rule or a library entry |
| 8 (Administration) | 23 | Administrative Appeal | 14 | prose — needs a rule or a library entry |
| 8 (Administration) | 24 | Judicial Appeal | 4 | prose — needs a rule or a library entry |
| 8 (Administration) | 25 | Nonconformity | 11 | prose — needs a rule or a library entry |
| 8 (Administration) | 26 | Code Enforcement Officer | 21 | prose — needs a rule or a library entry |
| 8 (Administration) | 27 | Planning Board | 25 | prose — needs a rule or a library entry |
| 8 (Administration) | 28 | Board Of Appeals | 10 | prose — needs a rule or a library entry |
| 8 (Administration) | 29 | Life Safety | 19 | prose — needs a rule or a library entry |

## 5. Shoreland

8 provisions of the Code mention shoreland. They are quoted here as written, without interpretation.

- `a1.s5.a.1` (General Standards, Adoption & Effect): This Code is adopted under the Municipal Home Rule Powers of the Maine Constitution, Article VIII-A and 30-A MRSA Chapter 141, and Chapter 187. Specific chapters of this Code are also adopted under specific statutory standards, including Mobile Home Parks, under 30-A MRSA Section 4358; Subdivisions, under 30-A MRSA Section 4404; Shoreland Standards, under 38 MRSA Sections 435449, and Floodplain Management, under PL. 90-488, the National Flood Insurance Act of 1968.
- `a3.s6.e.2.a` (Thoroughfares, New Thoroughfares): Any culvert or crossing within a stream, brook, or other water body, or within the Shoreland Zone, must be designed by a Maine-licensed civil engineer in accordance with Section 10 and the Newcastle Shoreland Zoning Ordinance.
- `a3.s7.f.4` (Thoroughfares, Driveways): **Safety floor.** Regardless of the number of dwelling units, an access way that crosses a stream, brook, or other water body, or that lies within the Shoreland Zone, shall meet the culvert and crossing standards of Section 10 and the Newcastle Shoreland Zoning Ordinance, designed by a Maine-licensed civil engineer as required by Section 6.E.2.a; and the reviewing authority may require a higher level of improvement than this Subsection specifies where grades, soils, drainage, traffic, or public-safety conditions warrant, supported by a written finding (Section 6.E.2.c).
- `a7.s41.b.2` (Use Standards, Marina, Recreation): See Shoreland Zoning Ordinance
- `a7.s55.b.1` (Use Standards, Resource Extraction): Ensure compliance with the Shoreland Zoning Ordinance.
- `a8.s9.d.1.a` (Administration, Application Types): Shoreland Zoning
- `a8.s19.d.4.f` (Administration, Variance): The property is not located in whole or in part within shoreland areas as described in Title 38, Section 435.; and,
- `a8.s27.a.4.a` (Administration, Planning Board): Shoreland

The portal loads these map layers: parcels, addresses, districts, streets. None of them maps a shoreland zone, so the builder can't yet tell whether a lot is in one.

**Question for the chair:** do the shoreland standards sit in the Core Zoning Code, or in a separate shoreland ordinance? And where can the portal get a map of the shoreland zone?

## 6. Existing permits and established uses on record

No portal data source carries the permits or established uses already on record for a lot. The builder needs them to tell someone "you're already covered".

**Question for the chair:** does the Town keep a record of permits and established uses by map and lot, and in what form (a spreadsheet, a database, paper files)?

