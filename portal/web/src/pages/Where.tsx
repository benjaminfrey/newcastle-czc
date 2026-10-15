import { Button, Card, Description, Form, Input, Label, Radio, RadioGroup, TextArea, TextField } from "@heroui/react";
import { useEffect, useState, type FormEvent } from "react";
import ParcelMap from "../components/ParcelMap";
import { getDistricts, getProperty, parcelAt, searchProperty, type Facts, type Hit } from "../api";
import { saveProperty } from "../property";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
                "October", "November", "December"];

// "2012-04-01" → "April 1, 2012", without time-zone surprises.
function longDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return `${MONTHS[m - 1]} ${d}, ${y}`;
}

// "004-036" → "Map 4, Lot 36"; "003-073-00B" → "Map 3, Lot 73-B".
function mapLotLabel(mapLot: string): string {
  const [map, ...lot] = mapLot.split("-");
  return `Map ${Number(map) || map}, Lot ${lot.map((p) => p.replace(/^0+(?=.)/, "")).join("-")}`;
}

function districtLine(f: Facts): { text: string; staffWillConfirm: boolean } {
  const named = f.districts.filter((d) => d.in_ruleset && d.name);
  const staffWillConfirm = f.districts.some((d) => !d.in_ruleset);
  if (named.length === 0) return { text: "District: staff will confirm.", staffWillConfirm: false };
  if (named.length === 1) return { text: `District: ${named[0].name}.`, staffWillConfirm };
  const [first, ...rest] = named;
  return {
    text: `This lot is in more than one district: ${first.name} (most of it), ${rest.map((d) => d.name).join(", ")}.`,
    staffWillConfirm,
  };
}

type Mode = "lookup" | "manual" | "saved";

const BUSY = "You've looked up a lot of places in the last minute. Please wait a minute and try again.";

export default function Where() {
  const [mode, setMode] = useState<Mode>("lookup");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Hit[] | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [facts, setFacts] = useState<Facts | null>(null);
  const [focus, setFocus] = useState<{ lon: number; lat: number } | null>(null);
  const [disputing, setDisputing] = useState(false);
  const [note, setNote] = useState("");
  const [unavailable, setUnavailable] = useState(false);
  const [districts, setDistricts] = useState<{ code: string; name: string }[]>([]);
  const [mapLot, setMapLot] = useState("");
  const [district, setDistrict] = useState("unsure");

  useEffect(() => {
    getDistricts().then(setDistricts);
  }, []);

  function goManual(lookupDown: boolean) {
    setUnavailable(lookupDown);
    setMode("manual");
  }

  async function showParcel(id: number) {
    const f = await getProperty(id);
    if (f === "unavailable") return goManual(true);
    if (f === "busy") return setMessage(BUSY);
    if (!f) return setMessage("We couldn't load that lot. Try another search, or tap your lot on the map.");
    setMessage(null);
    setDisputing(false);
    setFacts(f);
  }

  async function onSearch(e: FormEvent) {
    e.preventDefault();
    if (query.trim().length < 2) return;
    const res = await searchProperty(query.trim());
    if (res === "unavailable") return goManual(true);
    if (res === "busy") return setMessage(BUSY);
    setHits(res);
    setMessage(res.length ? null : "We couldn't find that. Try just the house number and street, or your map and lot.");
  }

  async function pickHit(h: Hit) {
    if (h.parcel_id) return showParcel(h.parcel_id);
    setFacts(null);
    setFocus({ lon: h.lon, lat: h.lat });
    setMessage("We found that address but not the lot it's on. Tap your lot on the map.");
  }

  async function onPick(lon: number, lat: number) {
    const id = await parcelAt(lon, lat);
    if (id === "unavailable") return goManual(true);
    if (id === "busy") return setMessage(BUSY);
    if (id === null) return setMessage("There's no lot at that spot. Try tapping inside your lot's lines.");
    return showParcel(id);
  }

  function confirm(disputed: boolean) {
    if (!facts) return;
    const main = facts.districts[0];
    saveProperty({
      source: "lookup", parcel_id: facts.parcel_id, map_lot: facts.map_lot,
      district_code: main && main.in_ruleset ? main.code : null,
      disputed, note: disputed ? note.trim() : "", as_of: facts.as_of.parcels,
    });
    setMode("saved");
  }

  function saveManual(e: FormEvent) {
    e.preventDefault();
    saveProperty({
      source: "manual", parcel_id: null, map_lot: mapLot.trim(),
      district_code: district === "unsure" ? null : district, disputed: false, note: "", as_of: null,
    });
    setMode("saved");
  }

  if (mode === "saved") {
    return (
      <Card>
        <Card.Header>
          <Card.Title>Saved.</Card.Title>
          <Card.Description>The next steps are coming soon.</Card.Description>
        </Card.Header>
      </Card>
    );
  }

  if (mode === "manual") {
    return (
      <Card>
        <Card.Header>
          <Card.Title>Your property</Card.Title>
          <Card.Description>
            {unavailable
              ? "We can't look up properties right now. You can enter your property's details yourself."
              : "Enter your property's details yourself."}{" "}
            The Code Enforcement Officer will check them.
          </Card.Description>
        </Card.Header>
        <Card.Content>
          <Form onSubmit={saveManual} className="flex flex-col gap-4">
            <TextField isRequired value={mapLot} onChange={setMapLot}>
              <Label>Map and lot</Label>
              <Input />
              <Description>It's on your property tax bill, for example "Map 4, Lot 36" or "4-36".</Description>
            </TextField>
            <RadioGroup value={district} onChange={setDistrict} name="district">
              <Label>District</Label>
              {[...districts, { code: "unsure", name: "I'm not sure" }].map((d) => (
                <Radio key={d.code} value={d.code}>
                  <Radio.Content>
                    <Radio.Control>
                      <Radio.Indicator />
                    </Radio.Control>
                    {d.name}
                  </Radio.Content>
                </Radio>
              ))}
            </RadioGroup>
            <Button type="submit" variant="primary">Save</Button>
          </Form>
        </Card.Content>
      </Card>
    );
  }

  const district_ = facts ? districtLine(facts) : null;
  // Article 2 §5; the chair's ruling of 2026-10-15 on who builds there and how.
  const civic = facts?.districts.find((d) => d.code === "SD-Civic");
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Where is your project?</h1>
      <Form onSubmit={onSearch} className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <TextField value={query} onChange={setQuery} className="flex-1">
          <Label>Street address, or map and lot</Label>
          <Input />
        </TextField>
        <Button type="submit" variant="primary">Search</Button>
      </Form>

      {hits && hits.length > 0 && (
        <ul className="flex flex-col gap-1" aria-label="Search results">
          {hits.map((h) => (
            <li key={`${h.label}-${h.lon}-${h.lat}`}>
              <Button variant="ghost" onPress={() => pickHit(h)}>{h.label}</Button>
            </li>
          ))}
        </ul>
      )}

      {message && <p role="status">{message}</p>}

      <ParcelMap selected={facts?.geometry ?? null} focus={focus} onPick={onPick} />
      <p className="text-sm">Or tap your lot on the map.</p>

      {facts && district_ && (
        <Card>
          <Card.Header>
            <Card.Title>Here's what we found</Card.Title>
          </Card.Header>
          <Card.Content className="flex flex-col gap-2">
            <p className="font-semibold">{mapLotLabel(facts.map_lot)}</p>
            <p>{district_.text}</p>
            {district_.staffWillConfirm && <p>Part of this lot is in an area staff will confirm.</p>}
            {civic && (
              <p>
                {civic.share >= 0.99 ? "This lot is" : "Part of this lot is"} Town-owned land in the Civic district.
                Only the Town builds on Civic land: Town Meeting votes on it, on the Select Board's
                recommendation, and no permit application is made through this site.
              </p>
            )}
            <p>About {facts.acres} acres (measured from the map).</p>
            {facts.streets.map((s) => (
              <p key={`${s.name}-${s.type}`}>
                About {s.frontage_ft} ft along {s.name}{s.type_name ? `, a ${s.type_name}` : ""}.
              </p>
            ))}
            <p className="text-sm">
              Lot lines from the Town's tax maps as of {longDate(facts.as_of.parcels)}. District from a tracing
              of the District Map. The Code Enforcement Officer confirms all of this when you apply.
            </p>
          </Card.Content>
          <Card.Footer className="flex flex-col items-start gap-3">
            {!disputing ? (
              <div className="flex flex-wrap gap-2">
                <Button variant="primary" onPress={() => confirm(false)}>Yes, this is my property</Button>
                <Button variant="secondary" onPress={() => setDisputing(true)}>This doesn't look right</Button>
              </div>
            ) : (
              <div className="flex w-full flex-col gap-2">
                <TextField value={note} onChange={setNote}>
                  <Label>What looks wrong?</Label>
                  <TextArea />
                  <Description>Staff will see this. You can still go on with your application.</Description>
                </TextField>
                <Button variant="primary" onPress={() => confirm(true)}>Save</Button>
              </div>
            )}
          </Card.Footer>
        </Card>
      )}

      <div>
        <Button variant="ghost" onPress={() => goManual(false)}>I can't find my property</Button>
      </div>
    </div>
  );
}
