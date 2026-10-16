# Screener rules for approval (adopted-v1.0)

Every entry below is a **draft**. Production will not show applicants any answer that rests on a draft. Each entry shows what applicants would read, the Code section it rests on, and that section quoted from the adopted ruleset.

To approve, change `status: draft` to

```yaml
status: approved
approved_by: <name>
approved_on: 2026-10-15
```

## Questions from drafting

1. **An owner's own home.** The use table has no use for a home the owner lives in: *Residence* is defined as a dwelling "rented, leased, let, or hired out". So someone building their own house is told only about the Small Project Plan, and has no use to choose. Is that right, or does an owner-occupied home need something more?
2. **Residential Companion permits have no time limit in the Code's clocks.** §17.c.1 says the procedure follows §15.D, but the clock for §15.d.1 lists only Use and Expanded Use permits. The screener therefore shows no time limit for a Residential Companion permit. Should it show 30 days?
3. **Dividing into fewer than three lots** is not a subdivision (§12.b.1). The draft tells the person to ask the Code Enforcement Officer rather than guessing what else applies.
4. **A Large Project Plan is the Code Enforcement Officer's** (§11.c.1), though §11.d.4 also gives the Planning Board a hearing and decision in some cases. The draft names the CEO as reviewer.
5. **Use-table codes become applications** as follows: `u` → use permit, `rc` → residential companion, `ex` → expanded use, `sp` → special permit; a blank cell means the Code doesn't list the use in that district.

## Applications (`applications.yaml`)

### `use_permit` — Use Permit

- Applicants read: Permission to start a new use of land or a building, or to change from one use to another.
- Reviewer: Code Enforcement Officer
- Time limits shown: 30 calendar days
- Apply on this site: yes
- Rests on Art. 8 §15.b.1:

  > Applies to all applications seeking to engage in a new Use or a change of Use on a parcel of land, in a building, or group of buildings.

### `residential_companion` — Residential Companion Use Permit

- Applicants read: Permission for a use that goes along with a home on the same lot.
- Reviewer: Code Enforcement Officer
- Time limits shown: none
- Apply on this site: no (Town Office)
- Rests on Art. 8 §17.b.1:

  > Applies to all applications seeking to engage in a new Residential Companion Use or a change of Use either to or from a Residential Companion Use.

### `expanded_use` — Expanded Use Permit

- Applicants read: Permission for a use the Code normally places in busier districts.
- Reviewer: Planning Board
- Time limits shown: 30 calendar days
- Apply on this site: no (Town Office)
- Rests on Art. 8 §16.b.1:

  > Applies to all applications seeking to engage in a new Expanded Use or a change of Use either to or from an Expanded Use.

### `special_permit` — Special Permit

- Applicants read: A Planning Board decision, after a public hearing, on a use the Code allows only case by case.
- Reviewer: Planning Board
- Time limits shown: 30 calendar days, 45 calendar days
- Apply on this site: no (Town Office)
- Rests on Art. 8 §18.b.1:

  > Special permits may only be requested as specifically authorized by this Code.

### `small_project_plan` — Small Project Plan

- Applicants read: The Code Enforcement Officer's review of a new building, addition or site change up to 10,000 square feet.
- Reviewer: Code Enforcement Officer
- Time limits shown: 10 calendar days
- Apply on this site: yes
- Rests on Art. 8 §10.b.1:

  > All new buildings and accessory buildings up to 10,000 sf in gross floor area.

### `large_project_plan` — Large Project Plan

- Applicants read: A fuller review of a building over 10,000 square feet, a large parking lot, or a project with big effects on its surroundings.
- Reviewer: Code Enforcement Officer
- Time limits shown: 45 calendar days
- Apply on this site: no (Town Office)
- Rests on Art. 8 §11.b.2:

  > All new buildings and accessory buildings over 10,000 sf in gross floor area.

### `subdivision` — Subdivision

- Applicants read: The Planning Board's review of dividing land into three or more lots, or building three or more homes.
- Reviewer: Planning Board
- Time limits shown: none
- Apply on this site: no (Town Office)
- Rests on Art. 8 §12.b.1:

  > The division of a parcel of land into 3 or more lots within any 5 year period that begins on or after September 23, 1971.

### `entrance_permit` — Driveway and Entrance Permit

- Applicants read: Permission for a new driveway or entrance onto a street or road, or for moving one.
- Reviewer: Code Enforcement Officer
- Time limits shown: none
- Apply on this site: yes
- Rests on Art. 3 §13.c.1:

  > The Code Enforcement Officer reviews and approves:
  > a. Driveway construction and relocation permits.
  > b. Entrance permits.
  > c. General maintenance permits where required.

## Rules (`rules.yaml`)

### `civic-land`

- When: `{'eq': ['property.civic', True]}`
- Then: town only
- Rests on Art. 2 §5.b.1:

  > Lots designated on the Zoning Map as SD-Civic are municipally owned and not subject to the standards of this Ordinance.

### `use-from-table`

- When: `{'all': [{'has': ['project', 'use']}, {'known': 'use_key'}]}`
- Then: use table
- Rests on Art. 8 §15.b.1:

  > Applies to all applications seeking to engage in a new Use or a change of Use on a parcel of land, in a building, or group of buildings.

### `use-not-chosen`

- When: `{'all': [{'has': ['project', 'use']}, {'not': {'known': 'use_key'}}]}`
- Then: Choose the use you have in mind to see which permit the Code calls for.
- Rests on Art. 8 §15.b.1:

  > Applies to all applications seeking to engage in a new Use or a change of Use on a parcel of land, in a building, or group of buildings.

### `small-project`

- When: `{'all': [{'has': ['project', 'build']}, {'lte': ['building.gross_floor_area_sf', 10000]}]}`
- Then: names the small project plan
- Rests on Art. 8 §10.b.1:

  > All new buildings and accessory buildings up to 10,000 sf in gross floor area.

### `large-project`

- When: `{'all': [{'has': ['project', 'build']}, {'gt': ['building.gross_floor_area_sf', 10000]}]}`
- Then: names the large project plan
- Rests on Art. 8 §11.b.2:

  > All new buildings and accessory buildings over 10,000 sf in gross floor area.

### `building-size-unknown`

- When: `{'all': [{'has': ['project', 'build']}, {'not': {'known': 'building.gross_floor_area_sf'}}]}`
- Then: Up to 10,000 square feet of floor area is a Small Project Plan; more is a Large Project Plan. Measure the floor area of every storey you're adding.
- Rests on Art. 8 §10.b.1:

  > All new buildings and accessory buildings up to 10,000 sf in gross floor area.

### `three-or-more-homes`

- When: `{'all': [{'has': ['project', 'build']}, {'gte': ['building.dwelling_units', 3]}]}`
- Then: names the subdivision
- Rests on Art. 8 §12.b.3:

  > The construction or placement of 3 or more dwelling units.

### `divide-three-or-more`

- When: `{'all': [{'has': ['project', 'divide']}, {'gte': ['division.lots_after', 3]}]}`
- Then: names the subdivision
- Rests on Art. 8 §12.b.1:

  > The division of a parcel of land into 3 or more lots within any 5 year period that begins on or after September 23, 1971.

### `divide-fewer`

- When: `{'all': [{'has': ['project', 'divide']}, {'lt': ['division.lots_after', 3]}]}`
- Then: Dividing into fewer than three lots isn't a subdivision under the Code, but other rules may still apply. The Code Enforcement Officer can tell you what you need.
- Rests on Art. 8 §12.b.1:

  > The division of a parcel of land into 3 or more lots within any 5 year period that begins on or after September 23, 1971.

### `driveway`

- When: `{'has': ['project', 'driveway']}`
- Then: names the entrance permit
- Rests on Art. 3 §7.b.1:

  > Applies to new Driveways and to the relocation of existing Driveways.

### `maine-dot`

- When: `{'all': [{'has': ['project', 'driveway']}, {'eq': ['property.on_state_highway', True]}]}`
- Then: Your lot is on a State highway, so the Maine Department of Transportation must also approve the entrance. Bring a copy of their permit to the Town.
- Rests on Art. 3 §12.d.1:

  > An entrance onto a State Highway requires a MaineDOT entrance permit under 23 MRSA §704 in addition to any permit required by this Article.

### `something-else`

- When: `{'has': ['project', 'other']}`
- Then: Tell the Code Enforcement Officer what you have in mind; they can say what, if anything, you need.
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

- `residence` — **Residence**: A house, apartment or room that is rented out to live in.
  - Code: A dwelling unit used, intended, or designed to be rented, leased, let, or hired out to be occupied for living purposes.
- `tourist_rental` — **Tourist Rental**: Renting out a home, or part of one, for stays shorter than 30 days.
  - Code: The rental of a dwelling unit, or a portion of a dwelling unit, on an overnight or short-term basis for less than 30 days at a time.
- `bed_breakfast` — **Bed & Breakfast**: Guest rooms for overnight stays in a home where the owner lives.
  - Code: When a permanent resident provides rooms within a single unit residential building for temporary, overnight lodging for compensation in guest rooms with no in-room cooking facilities. A bed and breakfast may include dining facilities and meeting rooms.
- `rooming_house` — **Rooming House**: A building where unrelated people rent rooms and share kitchens or bathrooms.
  - Code: A structure occupied, designed, or intended to be occupied by individuals who may share common areas and facilities, but do not form a single household, and do not provide compensation under a single lease for occupancy. A rooming unit provides sleeping accommodations, but no in-room cooking facilities.
- `dormitory` — **Dormitory**: Housing run by a school or college for its students or staff.
  - Code: Residential housing exclusively occupied by full or part-time students and/or educational staff and owned or operated by an educational institution.
- `mobile_home_park` — **Mobile Home Park**: A park for mobile homes (the Town's Mobile Home Parks Ordinance also applies).
  - Code: See Mobile Home Parks Ordinance

### A shop, office or service

- `retail_service_general` — **Retail & Service, General**: A shop or service you walk into and buy from on the spot, like a store or a hair salon.
  - Code: A business that provides goods or services directly to the consumer, where such goods or services are available for immediate purchase on the premises by the purchaser.
- `retail_service_heavy` — **Retail & Service, Heavy**: A business with goods displayed or stored outdoors, like a lumber yard or a garden center.
  - Code: A retail and service business with permanent outdoor display, service, and storage areas, such as vendors of lumber and building supplies, landscaping supplies and equipment, industrial equipment, commercial and recreational vehicles, watercraft, and outdoor structures such as prefabricated sheds, decks and patios, swimming pools, and play equipment.
- `retail_firearm_sales_facility` — **Retail Firearm Sales Facility**: A business that displays or sells firearms.
  - Code: A business which publicly displays or offers Firearms, as defined by the Code of Federal Regulations, Title 27, Chapter I, Subchapter C, §53.11 Meaning of terms, for sale to the public, where such Firearms are available for purchase on the premises. Public display or offer does not include online-only displays or offers.
- `packaged_liquor` — **Packaged Liquor**: A store selling beer, wine or spirits to take away.
  - Code: Any alcoholic beverage sales establishment involving the sale of alcohol where beer, wine or distilled spirits are sold for off-sale consumption.
- `adult_establishment` — **Adult Establishment**: A business selling explicit sexual material, restricted to adults.
  - Code: A business that sells or disseminates explicit sexual material, and at which access to the public display of explicit sexual material is restricted by law to persons 18 years of age or older.
- `banking_services` — **Banking Services**: A bank, credit union or other place that lends or keeps money.
  - Code: Uses related to the exchange, lending, borrowing, and safe-keeping of money.
- `office_small` — **Office, Small**: A small business office for administration or consulting (not medical).
  - Code: An small office use involves the conduct of business relating to administration, clerical work, and consulting activities, not including medical offices, retail, or service uses. May include single or multiple companies within one unit or building. A small office has up to 5 workers in a single building and 6 parking spaces per lot.
- `office_medium` — **Office, Medium**: A mid-sized business office for administration or consulting (not medical).
  - Code: A medium office use involves the conduct of business relating to administration, clerical work, and consulting activities, not including medical offices, retail, or service uses. May include single or multiple companies within one unit or building. A medium office has up to 35 workers in a single building and no parking space limitations.
- `office_large` — **Office, Large**: A large business office for administration or consulting (not medical).
  - Code: A medium office use involves the conduct of business relating to administration, clerical work, and consulting activities, not including medical offices, retail, or service uses. May include single or multiple companies within one unit or building. A large office has no maximum number of workers in a single building and no parking space limitations.
- `health_care_provider` — **Health Care Provider**: A doctor's, dentist's or therapist's office for outpatient care.
  - Code: An office providing outpatient health services involving the diagnosis and treatment of physical or mental ailments and disorders, including doctors, dentists, mental health practitioners, physical therapists, and their substantial equivalents.
- `animal_care_indoor` — **Animal Care, Indoor**: A vet's office or other indoor care for other people's animals.
  - Code: A facility where animals not owned by the proprietor are sheltered and fed, and where all activities are located indoors. Includes veterinarian offices, grooming services, or training services for dogs, cats, and other household pets.
- `funeral_services` — **Funeral Services**: A funeral home.
  - Code: A facility where the deceased are prepared for burial display and for rituals before burial or cremation. Such facilities may include chapels and showrooms for the display and sale of caskets, vaults, urns, and other items related to burial services.
- `commercial_school` — **Commercial School**: A school teaching particular skills for a fee, like a driving or art school.
  - Code: A school that teaches industrial, clerical, managerial, commercial, artistic, or other select skills; conducts a commercial enterprise, such as a driving school; or a privately operated school that does not offer a complete educational curriculum.
- `research_laboratory` — **Research Laboratory**: A lab for research and development.
  - Code: A facility for research and development that does not involve the use of human testing, animal husbandry, incinerators, heavy equipment, mass manufacturing, fabrication, processing, or sale of products.
- `vehicle_rental_or_sales` — **Vehicle Rental or Sales**: Selling, leasing or renting cars, motorcycles or similar vehicles.
  - Code: A business that sells, leases, or rents automobiles, vans, three-wheelers, motorcycles, scooters, or other powered personal transportation or conveyance, and which may include on-site facilities for the repair and service of vehicles sold, leased, or rented. This does not include the sale, lease, or rental of recreational vehicles, commercial vehicles, or watercraft, which is considered a heavy retail and service use.
- `gas_station` — **Gas Station**: Selling fuel for vehicles.
  - Code: A facility engaged in the retail sales of personal or commercial vehicle fuels.
- `car_wash` — **Car Wash**: Washing vehicles, by machine or by hand.
  - Code: An establishment for the washing of motor vehicles, which may employ production-line methods, mechanical devices, staffed hand wash facilities, or unstaffed self-wash facilities.
- `drive_through_facility` — **Drive-Through Facility**: Serving customers who stay in their cars, through a window or a machine.
  - Code: A facility that dispenses goods through an attendant window or automated machine to persons remaining in vehicles in a designated drive aisle.

### Food, drink or places to stay

- `restaurant_cafe` — **Restaurant & Café**: A restaurant, cafe or takeaway.
  - Code: A business where food and beverages are prepared and served to patrons for consumption either on-premises or off-premises.
- `bar_or_tavern` — **Bar or Tavern**: A bar or tavern serving food and alcohol to have there.
  - Code: A business that serves food and alcoholic beverages for on-premises consumption.
- `live_entertainment` — **Live Entertainment**: Live music, performance or other entertainment by people present in person.
  - Code: Any activity provided for pleasure, quiet enjoyment, recreation, relaxation, diversion or other similar purpose by a person or persons who are physically present when providing an activity to a patron or group of patrons who are physically present.
- `hotel_hostel` — **Hotel & Hostel**: A hotel, inn or hostel.
  - Code: A commercial building(s) with guest rooms designed primarily for sleeping, and usually including a lobby, reception area, conference rooms, recreational amenities, and common kitchen cooking facilities providing meals for paying guests in a dining rooms or restaurants.
- `campground` — **Campground**: Sites for tents or recreational vehicles.
  - Code: A site where one or more lots are used, or are intended to be used, by campers with tents or recreational vehicles.

### Farming and land

- `commercial_agriculture` — **Commercial Agriculture**: Growing crops or raising livestock to sell.
  - Code: The commercial planting, cultivating, producing, growing, and harvesting of agricultural or horticultural products, the raising of livestock and poultry, and any work performed in conjunction with the above farm operations, including the packing, drying, and storing of products produced on-premises.
- `aquaculture` — **Aquaculture**: Farming fish, shellfish or seaweed to sell.
  - Code: The commercial production of cultured fish, shellfish, seaweed, or other marine plants for human and animal consumption, including all cultivating activities occurring at hatcheries or nurseries, from the egg, larval or spore stages to the transfer of the product to a growing site and all cultivating activities occurring on water, from the receipt of fish, shellfish or other marine plants from onshore facilities to the delivery of harvested products to onshore facilities for processing.
- `farm_vendor_market` — **Farm/Vendor Market**: A market where several farmers or vendors sell from their own stands.
  - Code: The direct sales of goods and/or products by multiple farmers or vendors from individual booths, tables, or stands, whether indoors or outdoors.
- `animal_care_outdoor` — **Animal Care, Outdoor**: Boarding, sheltering or training other people's animals, with outdoor areas.
  - Code: A facility where animals not owned by the proprietor are sheltered and fed. Includes animal rescue shelters, boarding facilities, pet resorts/hotels, or training services for dogs, cats, and other household pets.
- `stables_riding_center` — **Stables/Riding Center**: Stables for horses, riding lessons or shows.
  - Code: A structure or land used, designed, and arranged for the care and shelter of equines, for riding, shows, or training, which may include horses not boarded on-site.
- `resource_extraction` — **Resource Extraction**: Removing soil, rock, timber or water from the land to sell.
  - Code: Any use that involves the removal of raw materials from the lot, such as soil, rock, timber, or water for commercial activity.

### Making, fixing or storing things

- `industrial_artisan` — **Industrial, Artisan**: Small-scale making or assembling, like a woodworking or pottery shop.
  - Code: A manufacturing use involving small-scale production or assembly with no noxious by-products, and which may include a showroom as well as incidental storage, sales, and distribution of products.
- `industrial_general` — **Industrial, General**: Light manufacturing, outdoor storage or trucking.
  - Code: Uses that are associated with retail sales, outdoor storage, or light manufacturing of finished or semi-finished products and may include trucking associated with the movement of materials or wholesale distribution.
- `industrial_heavy` — **Industrial, Heavy**: Large-scale processing or manufacturing with noise, dust or other effects beyond the lot.
  - Code: The processing, manufacturing, compounding, or storage of materials, products, or energy, where the scale and method of operation regularly produce noise, heat, glare, dust, smoke, fumes, odors, vibration, and that may result in external impacts beyond the lot lines of the property. May regularly employ hazardous material or produce hazardous by-products.
- `vehicle_repair` — **Vehicle Repair**: A garage that repairs or services vehicles.
  - Code: A business that repairs, installs, or maintains automobiles, small trucks or vans, motorcycles, motor homes, or recreational vehicles or that wash, clean, or otherwise protect the exterior or interior surfaces of these types of vehicles.
- `outdoor_storage` — **Outdoor Storage**: Keeping equipment, vehicles or materials outdoors for a business on the same lot.
  - Code: The outdoor keeping of equipment, vehicles, waste, and any materials associated with uses or activities occurring within buildings on the same lot for a period greater than 48 hours.
- `self_storage_facility` — **Self-Storage Facility**: Storage units rented out to the public.
  - Code: A facility where individual secured areas inside a structure are rented for short-term storage of a variety of non-hazardous, non-perishable durable goods and where the lessee has direct access and responsibility for loading and unloading the storage.
- `marina_dry_storage` — **Marina, Dry Storage**: Storing boats out of the water, in racks or similar.
  - Code: A site used for the long-term dry storage of recreational watercraft in racks or other storage systems, and which may include ancillary repair facilities for watercraft.
- `junk_salvage_yard` — **Junk/Salvage Yard**: A yard that breaks up, sorts or stores scrap or salvage.
  - Code: Outdoor establishments primarily engaged in assembling, breaking up, sorting, and the temporary storage and distribution of recyclable or reusable scrap and waste materials, including auto wreckers engaged in dismantling automobiles for scrap, and the incidental wholesale or retail sales of parts from those vehicles. An area or building where waste or scrap materials are bought, sold, exchanged, stored, baled, packed, disassembled, or handled for reclamation, disposal or other like purposes, including but not limited to scrap iron and other metals, paper, rags, rubber tires, and bottles. A junk or salvage yard or building includes an auto wrecking yard or building.
- `recycling_facility` — **Recycling Facility**: A place that takes in and processes recyclable materials.
  - Code: A facility that accepts materials, such as dry paper, glass, cans, or plastics, for storage and processing by power-driven equipment for the subsequent reuse in the secondary materials market.

### Recreation, community, care and schools

- `amusement_indoor` — **Amusement, Indoor**: Indoor entertainment or sport, like a cinema or a bowling alley.
  - Code: A commercial facility for spectator and participatory uses conducted within an enclosed building, such as movie theaters, sports arenas, bowling alleys, tumbling centers, skating centers, roller rinks, and pool halls.
- `amusement_outdoor` — **Amusement, Outdoor**: Outdoor entertainment or sport, like a fairground or a mini-golf course.
  - Code: A commercial facility for spectator and participatory uses conducted outdoors or within partially enclosed structures, such as fairgrounds, campgrounds, batting cages, drive-in movie theater, recreational vehicle parks, petting zoos, golf courses, miniature golf courses, and amusement parks.
- `assembly` — **Assembly**: A place for meetings, services, events or programs.
  - Code: A facility that has organized services, meetings, events, or programs to benefit, educate, entertain, or promote discourse in a public or private setting. Examples include community centers, places of worship, meeting or lecture halls, exhibition rooms, or auditoria.
- `cultural_facility` — **Cultural Facility**: A museum, cultural center or historical society open to the public.
  - Code: A facility open to the public for cultural services and exhibitions including, but not limited to, museums, cultural centers, historical societies, and libraries operated by a government or non-profit establishment.
- `health_fitness_studio` — **Health/Fitness Studio**: A place for exercise, yoga or similar classes.
  - Code: A facility that provides interactive classes, personal or small group instruction, or other activities related to the improvement of the body, mind, and soul.
- `marina_recreation` — **Marina, Recreation**: Docks or moorings for recreational boats, on the water.
  - Code: A facility that has frontage on navigable water and allows for the short- or long-term docking and mooring of boats and that may provide supply, repair, and other services.
- `private_club_or_lodge` — **Private Club or Lodge**: A club or lodge open to members or invited guests.
  - Code: A facility operated for an organization, which is open to people upon invitation, nomination, or payment of fees or dues, for social, recreational, and/or entertainment activities.
- `college_university` — **College/University**: A college or university.
  - Code: A post-secondary institution for higher learning that grants associate, bachelor, masters, or doctoral degrees, and theological schools.
- `primary_secondary_school` — **Primary/Secondary School**: An elementary, middle or high school.
  - Code: A public, private, or parochial institution with a primary function of offering instruction at any of all primary or secondary education levels, inclusive of kindergarten through the 12th grade. This use shall not include businesses that offer exclusively recreational classes, such as art classes, musical instruction, or other similar classes open to the general public.
- `day_care_center` — **Day Care Center**: Licensed day care run alongside a home.
  - Code: A residential companion use that provides licensed care in a protective setting for children or elderly or disabled adults.
- `day_care_facility` — **Day Care Facility**: A licensed day care for children or adults.
  - Code: A facility where licensed care, protection, and supervision is provided in a protective setting for children or adults, with or without compensation, on a regular basis away from a primary residence.
- `hospital` — **Hospital**: A hospital.
  - Code: A facility that provides health, medical, or surgical care to the sick or injured and contains offices integral to function of the facility.
- `human_service_facility` — **Human Service Facility**: Services for people who need help because of age, disability, addiction, illness or injury.
  - Code: An establishment that provides services to persons in need of assistance due to age, physical or mental disability, addiction, illness, or injury, that does not provide residential dwelling units.
- `residential_care_facility` — **Residential Care Facility**: A licensed home providing round-the-clock care.
  - Code: A licensed care facility that provides 24-hour medical or non-medical care to persons in need of personal services, supervision, protection, or assistance essential for sustaining the activities of daily living. Residential care facilities include nursing homes, independent living, assisted living, continuum of care, and hospice facilities.
- `food_pantry` — **Food Pantry**: A not-for-profit giving out food or essentials free or at low cost.
  - Code: A not-for-profit use that distributes or facilitates the giving of food, clothing, and/or other essential items at no charge or for less than fair market value to persons in need of assistance.

### Transport, parking and utilities

- `dispatch_service` — **Dispatch Service**: A base for taxis, ambulances, tow trucks or buses.
  - Code: The storage and dispatch of ambulances, taxis, limousines, armored cars, tow trucks, buses, and similar vehicles for specialized transportation, including where ambulance crews not located at a hospital or fire department stand by for emergency calls, ancillary professional offices, and/or minor vehicle service and maintenance repair.
- `district_energy_system` — **District Energy System**: An energy system shared by several properties.
  - Code: A community-based energy system shared by property owners for common use, or managed by a homeowners' association, institution, or similar organization.
- `utilities_services` — **Utilities & Services**: Buildings or structures for electricity, internet, gas, water or similar services.
  - Code: Buildings and structures that provide or facilitate the transmission of services consumed by the public including electricity, Internet, natural gas, water, and sewage.
- `paid_parking_lot` — **Paid Parking Lot**: A parking lot open to the public for a fee.
  - Code: A non-accessory parking lot made available to the general public in exchange for a fee.

