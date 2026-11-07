import type { Needs, ProjectState } from "../projects";
import type { Ending } from "./api";
import { guide } from "./fixtures";
import { check } from "./turns/fixtures";

export const ending = (over: Partial<Ending> = {}): Ending => ({
  kind: "ready", title: "Your application is ready to send", body: "Here is what your project needs.", entry: null,
  settled: [{ turn_id: "floor_area", check: check({ value: 1800 }) }], unsettled: [], reviews: [], allowed_uses: [],
  not_listed: [], notes: [], ...over,
});

export const NEEDS: Needs = {
  permits: [{ key: "building_permit", name: "Building Permit", application_fee: 30, application_fee_words: "$30", reviews: [
    { review_key: "small_project_plan", use_key: null, name: "Small Project Plan", code_name: "Small Project Plan",
      plain: "The Code Enforcement Officer reviews your plan.", reviewer: "Code Enforcement Officer", certainty: "needed",
      in_portal: true, districts: [], fee: 0, fee_words: "No permit fee", clocks: [] }] }],
  application_fees_total: 30, permit_fees_total: 0, application_fees_vary: false, notes: [], not_listed: [], town_only: false,
};

export const project = (over: Partial<ProjectState> = {}): ProjectState => ({
  id: "p1", title: "A new house", status: "draft", revision: 9, ruleset_key: "adopted-v1.0", submitted_at: null,
  property: { source: "lookup", parcel_id: 1, map_lot: "012-034", facts: {}, parcels_as_of: null, verified: true, disputed: false, note: "" },
  items: [], forms: {}, needs: NEEDS, answers: [], notes: [], attachments: [], missing: [],
  form: { key: "project", version: 1, ruleset_key: "adopted-v1.0", official_title: "Project", steps: [{ id: "about_you", title: "About you" }],
    sections: [{ id: "applicant", official_title: "Applicant", chapter: "a", show_if: null, repeat: null, step: "about_you", screens: [],
      fields: [{ id: "owner_name", label: "Who owns the property?" } as never] }] },
  ...over,
});

export const ended = (e: Partial<Ending> = {}) => guide({ current: null, step: null, ending: ending(e) });
