import { Button, Card, Description, Form, Input, Label, Radio, RadioGroup, TextArea, TextField } from "@heroui/react";
import { useEffect, useState, type FormEvent } from "react";
import { ChoiceTiles } from "../controls/Tiles";
import InsetGroup from "../shell/InsetGroup";
import type { FormField } from "../applications";
import ParcelMap from "../components/ParcelMap";
import { getDistricts, getProperty, parcelAt, searchProperty, type Facts, type Hit } from "../api";
import { saveProperty } from "../property";
import { loadAnswers } from "../screener";
import { useNavigate, useSearchParams } from "react-router";
import { longDate, mapLotLabel } from "../format";

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
  const navigate = useNavigate();
  const [params] = useSearchParams();
  // Starting an application sends people here first, then back (only to an /apply/ page).
  const next = params.get("next")?.startsWith("/apply/") ? params.get("next") : null;
  const [mode, setMode] = useState<Mode>(params.get("manual") === "1" ? "manual" : "lookup");
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
      district_codes: facts.districts.map((d) => d.code), on_state_highway: facts.on_state_highway,
      disputed, note: disputed ? note.trim() : "", as_of: facts.as_of.parcels,
    });
    afterSave();
  }

  // In the middle of "Do I need a permit?", go on to the next question.
  function afterSave() {
    if (next) return navigate(next);
    const answers = loadAnswers();
    if (!answers) return setMode("saved");
    navigate(answers.project.includes("use") && !answers.use_key ? "/start/use" : "/start/needs");
  }

  function saveManual(e: FormEvent) {
    e.preventDefault();
    saveProperty({
      source: "manual", parcel_id: null, map_lot: mapLot.trim(),
      district_code: district === "unsure" ? null : district,
      district_codes: district === "unsure" ? [] : [district], on_state_highway: null,
      disputed: false, note: "", as_of: null,
    });
    afterSave();
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
  const facing = (words: string, ok: boolean) => ({ value: words, key: words, label: words, ok });

  // The lot that was found is its own screen: what the Town's map says, and three answers.
  if (facts && district_) {
    const answers = [facing("Yes, this is my property", true), facing("This doesn't look right", false), facing("No, search again", false)];
    return (
      <section className="pane-push flex flex-col items-center gap-3 py-6 text-center">
        <h2 tabIndex={-1} data-screen-title className="text-[22px] font-semibold leading-tight outline-none">Is this your property?</h2>
        <div className="h-56 w-full max-w-xl overflow-hidden rounded-xl">
          <ParcelMap selected={facts.geometry ?? null} focus={focus} onPick={onPick} />
        </div>
        {!disputing ? (
          <ChoiceTiles field={{ id: "this_lot", label: "Is this your property?", official_label: "Is this your property?" } as FormField}
                       value={null} choices={answers}
                       onPick={(v) => (v === answers[0].value ? confirm(false) : v === answers[1].value ? setDisputing(true) : setFacts(null))} />
        ) : (
          <div className="flex w-full max-w-md flex-col gap-2 text-left">
            <TextField value={note} onChange={setNote}>
              <Label>What looks wrong?</Label>
              <TextArea />
              <Description>Staff will see this. You can still go on with your application.</Description>
            </TextField>
            <Button variant="primary" className="self-end" onPress={() => confirm(true)}>Save</Button>
          </div>
        )}
        <div className="w-full max-w-xl text-left">
          <InsetGroup footer={<>Lot lines from the Town's tax maps as of {longDate(facts.as_of.parcels)}. District from a tracing
            of the District Map. The Code Enforcement Officer confirms all of this when you apply.</>}>
            <InsetGroup.Row label="Map and lot"><span className="font-semibold">{mapLotLabel(facts.map_lot)}</span></InsetGroup.Row>
            <InsetGroup.Row label="District"><span>{district_.text.replace(/^District: /, "")}</span></InsetGroup.Row>
            {district_.staffWillConfirm && <InsetGroup.Row label="Note"><span>Part of this lot is in an area staff will confirm.</span></InsetGroup.Row>}
            {civic && (
              <InsetGroup.Row label="Civic land">
                <span>
                  {civic.share >= 0.99 ? "This lot is" : "Part of this lot is"} Town-owned land in the Civic district.
                  Only the Town builds on Civic land: Town Meeting votes on it, on the Select Board's
                  recommendation, and no permit application is made through this site.
                </span>
              </InsetGroup.Row>
            )}
            <InsetGroup.Row label="Size"><span>About {facts.acres} acres (measured from the map).</span></InsetGroup.Row>
            {facts.streets.map((st) => (
              <InsetGroup.Row key={`${st.name}-${st.type}`} label="Road">
                <span>About {st.frontage_ft} ft along {st.name}{st.type_name ? `, a ${st.type_name}` : ""}.</span>
              </InsetGroup.Row>
            ))}
          </InsetGroup>
        </div>
      </section>
    );
  }

  return (
    <section className="flex flex-col items-center gap-3 py-6 text-center">
      <h2 tabIndex={-1} data-screen-title className="text-[22px] font-semibold leading-tight outline-none">Where is the property?</h2>
      <p className="max-w-[46ch] text-[15px] text-[var(--app-secondary-label)]">Search for the address, or the map and lot from your tax bill, or tap your lot on the map.</p>
      <Form onSubmit={onSearch} className="flex w-full max-w-xl flex-col gap-2 text-left sm:flex-row sm:items-end">
        <TextField value={query} onChange={setQuery} className="flex-1">
          <Label>Street address, or map and lot</Label>
          <Input />
        </TextField>
        <Button type="submit" variant="primary">Search</Button>
      </Form>

      {hits && hits.length > 0 && (
        <ul className="flex w-full max-w-xl flex-col gap-1 text-left" aria-label="Search results">
          {hits.map((h) => (
            <li key={`${h.label}-${h.lon}-${h.lat}`}>
              <Button variant="ghost" onPress={() => pickHit(h)}>{h.label}</Button>
            </li>
          ))}
        </ul>
      )}

      {message && <p role="status">{message}</p>}

      <div className="w-full max-w-xl overflow-hidden rounded-xl">
        <ParcelMap selected={null} focus={focus} onPick={onPick} />
      </div>
      <p className="text-[13px] text-[var(--app-secondary-label)]">Or tap your lot on the map.</p>
      <Button variant="ghost" className="text-[var(--app-accent-text)]" onPress={() => goManual(false)}>I can't find my property</Button>
    </section>
  );
}
