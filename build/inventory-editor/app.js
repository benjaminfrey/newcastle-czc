/* ==========================================================================
 * Newcastle Thoroughfare Inventory Editor — client behaviour
 * Implements CONTRACT.md v1.0.0 (§5 HTTP API · §8 DOM · §9 state · §10 keyboard
 * · §11 geometry · §12 note text).
 *
 * No libraries, no build step, no network beyond 127.0.0.1.
 * `index.html` owns the static shell and every <template>; this file clones
 * them and never invents an element id outside §8.
 * ========================================================================== */
(function () {
  "use strict";

  /* ---------------------------------------------------------------- 0. utils */

  var CONTRACT_VERSION = "1.0.0";
  var METRES_TO_FEET = 3.280839895013123;
  var FEET_PER_MILE = 5280;
  var SVG_NS = "http://www.w3.org/2000/svg";

  /* Field order is normative for display and for note composition (§12). */
  var FIELD_ORDER = ["type", "present_use", "ownership", "row_ft", "traveled_ft", "nonconformity", "exclude"];
  var FIELD_LABEL = {
    type: "Type",
    present_use: "Present use",
    ownership: "Ownership",
    row_ft: "ROW width",
    traveled_ft: "Traveled way",
    nonconformity: "Nonconformity",
    exclude: "Excluded"
  };
  /* §10: 1–5 → S1–S5, 6,7,8,9,0 → R1–R5 */
  var DIGIT_TO_TYPE = { "1": "S1", "2": "S2", "3": "S3", "4": "S4", "5": "S5",
                        "6": "R1", "7": "R2", "8": "R3", "9": "R4", "0": "R5" };
  var TYPE_TO_DIGIT = { S1: "1", S2: "2", S3: "3", S4: "4", S5: "5",
                        R1: "6", R2: "7", R3: "8", R4: "9", R5: "0" };
  var TYPE_NONE_COLOR = "#BFBFBF";
  var AUTO_NOTE_KEY = "nczc.editor.autoNote";
  var PENDING_KEY   = "nczc.editor.pending";
  var CANCELLED = Object.freeze({ cancelled: true });

  function E(id) { return document.getElementById(id); }
  function qs(root, sel) { return root ? root.querySelector(sel) : null; }
  function qsa(root, sel) { return root ? Array.prototype.slice.call(root.querySelectorAll(sel)) : []; }
  function hasOwn(o, k) { return o != null && Object.prototype.hasOwnProperty.call(o, k); }

  /* Tolerant setters: a template may legitimately omit an optional sub-node. */
  function setText(root, sel, text) {
    var n = qs(root, sel);
    if (n) n.textContent = text == null ? "" : String(text);
    return n;
  }
  function setHidden(node, hidden) { if (node) node.hidden = !!hidden; }
  function toggleClass(node, cls, on) { if (node) node.classList.toggle(cls, !!on); }
  function on(node, ev, fn, opts) { if (node) node.addEventListener(ev, fn, opts); }

  function fmtInt(n) {
    if (n == null || isNaN(n)) return "—";
    return Math.round(n).toLocaleString("en-US");
  }
  function fmtFt(n) { return n == null || isNaN(n) ? "—" : fmtInt(n) + " ft"; }
  function fmtMi(n) {
    if (n == null || isNaN(n)) return "—";
    return (n / FEET_PER_MILE).toFixed(2) + " mi";
  }
  function fmtTime(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    return d.toLocaleTimeString("en-US", { hour12: false });
  }
  function basename(p) { return p ? String(p).split("/").pop() : ""; }
  function plural(n, one, many) { return n === 1 ? one : (many || one + "s"); }

  /* Case- and diacritic-insensitive haystack (§8.2 #filter-search). */
  function fold(s) {
    return String(s == null ? "" : s)
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  }

  function sameValue(a, b) {
    if (a == null && b == null) return true;
    if (a == null || b == null) return false;
    if (typeof a === "number" || typeof b === "number") return Number(a) === Number(b);
    return a === b;
  }

  function debounce(fn, ms) {
    var t = null;
    return function () {
      var args = arguments, self = this;
      if (t) clearTimeout(t);
      t = setTimeout(function () { t = null; fn.apply(self, args); }, ms);
    };
  }

  /* --------------------------------------------------------------- 1. state */

  var state = {
    loaded: false,
    contract: CONTRACT_VERSION,
    baseToken: null,
    inventoryToken: null,
    meta: {},
    types: [],
    typeByCode: new Map(),
    ownershipCategories: [],
    presentUseValues: [],
    drivewayDisplay: null,
    districts: [],
    maindotClasses: [],
    view: null,
    segments: [],
    segById: new Map(),
    roads: [],
    roadByKey: new Map(),
    orphans: [],
    counts: {},
    warnings: [],

    pending: new Map(),

    selection: new Set(),
    anchorId: null,
    focusId: null,

    filters: { search: "", type: "", family: "", district: "", ownership: "", use: "", override: "", pendingOnly: false },
    sort: { key: "name", dir: "asc" },
    collapsedRoads: new Set(),
    zoom: { k: 1, tx: 0, ty: 0 },
    dimFiltered: true,
    hoverId: null,

    saving: false,
    lastSave: null,
    autoNote: false,
    contractMismatch: false,

    /* derived / bookkeeping (not part of §9's persisted model) */
    visibleIds: [],        // passes filters, in rendered order
    visibleSet: new Set(),
    navIds: [],            // visibleIds minus segments inside collapsed roads
    visibleRoadKeys: [],
    rowById: new Map(),
    pathById: new Map(),
    titleById: new Map(),
    roadRowByKey: new Map(),
    effTypeCount: {},
    lastPayloadIds: [],
    dataError: false
  };

  /* Prototype nodes cloned per row (built once — cloning beats re-querying). */
  var protos = { segRow: null, roadRow: null, pendingItem: null, pendingField: null };

  /* ------------------------------------------------------- 2. type helpers */

  function typeInfo(code) { return code ? state.typeByCode.get(code) || null : null; }
  function typeColor(code) { var t = typeInfo(code); return t ? t.color : TYPE_NONE_COLOR; }
  function typeName(code) { var t = typeInfo(code); return t ? t.name : ""; }
  function typeLabel(code) { return code ? code + " — " + typeName(code) : "—"; }
  function typeIndex(code) {
    for (var i = 0; i < state.types.length; i++) if (state.types[i].code === code) return i;
    return 99;
  }
  function sortTypeCodes(codes) {
    return codes.slice().sort(function (a, b) { return typeIndex(a) - typeIndex(b); });
  }

  /* ------------------------------------------- 3. base / effective values */

  /* The on-disk truth a pending `from` is measured against (§9.1).
     Display and staging both use this so a revert is exact. */
  function baseValue(seg, field) {
    if (!seg) return null;
    if (field === "exclude") return seg.excluded === true;
    var v = seg[field];
    return v === undefined ? null : v;
  }

  /* The value the segment would carry in overrides.json if we saved right now:
     the staged `to` when there is one — INCLUDING an explicit null, which means
     "remove the key" — otherwise the on-disk truth.

     This is deliberately NOT effective(): effective() falls back to the disk
     value when `to` is null, because a removed override displays as whatever the
     inventory says. For deciding whether an action changes anything, a staged
     null is a real, different, staged value. Every no-op / would-change test
     must use this, or an action silently skips segments that already carry a
     conflicting pending edit and writes the earlier, wrong value instead. */
  function currentValue(seg, field) {
    var pc = state.pending.get(seg.id);
    if (pc && pc.kind === "set" && hasOwn(pc.fields, field)) return pc.fields[field].to;
    return baseValue(seg, field);
  }

  /* §9.2: effective(seg, field) = pending.to ?? seg[field] */
  function effective(seg, field) {
    var pc = state.pending.get(seg.id);
    if (pc && pc.kind === "set" && hasOwn(pc.fields, field)) {
      var to = pc.fields[field].to;
      if (to !== null && to !== undefined) return to;
    }
    return baseValue(seg, field);
  }
  function effType(seg) { return effective(seg, "type") || ""; }
  function effOwnership(seg) { return effective(seg, "ownership") || ""; }
  /* Art 3 §5.C.3.g. Reference only — it never changes the Type, which stays the
     Type that would apply on conversion. §7.C.8 is what makes an access way a
     Driveway, so a blank here (not yet reviewed) protects the owner just the same. */
  function effPresentUse(seg) { return effective(seg, "present_use") || ""; }
  function isDriveway(seg) { return effPresentUse(seg) === "Driveway"; }
  function effExcluded(seg) {
    var pc = state.pending.get(seg.id);
    if (pc && pc.kind === "set" && hasOwn(pc.fields, "exclude")) return pc.fields.exclude.to === true;
    return seg.excluded === true;
  }
  function isNoteOnly(seg) {
    var o = seg.override;
    if (!o) return false;
    var keys = Object.keys(o);
    return keys.length === 1 && keys[0] === "note";
  }
  /* ---- "odd one out" ----------------------------------------------------
     The v0.22 audit corrected 42 Types across 18 roads, and nearly every one
     was the same shape: a road that is uniformly one Type except for a segment
     or two the approximate District trace mis-typed (Academy Hill all S3 bar
     one R2; Main Street all S1 bar the pieces still typed as River Road).

     So: on a road of 3+ segments where one Type holds a strict majority, the
     segments that disagree with it are worth a look. That is a derived fact
     about the data, not a guess about the world — it says "this road is not
     internally consistent", which is checkable against the map, and never
     "this Type is wrong". Everything else the reviewers proposed (short +
     private + dead-end + arterial) would be inventing a rule the Code does not
     contain, so it is left out. */
  var oddCache = null;
  function invalidateOdd() { oddCache = null; }

  function oddOneOutSet() {
    if (oddCache) return oddCache;
    var out = new Set();
    state.roads.forEach(function (road) {
      var ids = road.segment_ids || [];
      if (ids.length < 3) return;
      var counts = {}, best = null, bestN = 0;
      ids.forEach(function (id) {
        var seg = state.segById.get(id);
        if (!seg) return;
        var t = effType(seg) || "";
        counts[t] = (counts[t] || 0) + 1;
        if (counts[t] > bestN) { bestN = counts[t]; best = t; }
      });
      if (best === null || bestN * 2 <= ids.length) return;   // no strict majority
      ids.forEach(function (id) {
        var seg = state.segById.get(id);
        if (seg && (effType(seg) || "") !== best) out.add(id);
      });
    });
    oddCache = out;
    return out;
  }

  function oddMajorityType(seg) {
    var road = state.roadByKey.get(seg.road_key);
    if (!road) return "";
    var counts = {}, best = "", bestN = 0;
    (road.segment_ids || []).forEach(function (id) {
      var s2 = state.segById.get(id);
      if (!s2) return;
      var t = effType(s2) || "";
      counts[t] = (counts[t] || 0) + 1;
      if (counts[t] > bestN) { bestN = counts[t]; best = t; }
    });
    return best;
  }

  function isDrift(seg) {
    var o = seg.override;
    return !!(o && o.type && o.type !== seg.type);
  }
  function existingNote(seg) {
    return seg && seg.override && typeof seg.override.note === "string" ? seg.override.note : null;
  }
  /* §11.2 — the server sends length_ft; recompute from geometry if it is absent
     so the column is never blank (identical formula, so the two agree). */
  function segLength(seg) {
    if (typeof seg.length_ft === "number") return seg.length_ft;
    if (seg.__lenFt === undefined) {
      var m = 0, g = seg.geometry || [];
      for (var i = 1; i < g.length; i++) {
        m += Math.hypot(g[i][0] - g[i - 1][0], g[i][1] - g[i - 1][1]);
      }
      seg.__lenFt = Math.round(m * METRES_TO_FEET * 10) / 10;
    }
    return seg.__lenFt;
  }
  function roadLength(road) {
    return road.segment_ids.reduce(function (a, id) {
      var s = state.segById.get(id);
      return a + (s ? segLength(s) : 0);
    }, 0);
  }
  function segTitle(seg) {
    var t = effType(seg);
    return seg.name + " #" + seg.seq + " — " + (t || "—") + " — " + fmtInt(segLength(seg)) + " ft";
  }

  /* ----------------------------------------------------------- 4. transport */

  function api(path, options) {
    var opts = options || {};
    var init = { method: opts.method || "GET", headers: { Accept: "application/json" }, cache: "no-store" };
    if (opts.body !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(opts.body);
    }
    return fetch(path, init).then(function (res) {
      return res.text().then(function (text) {
        var data = null;
        try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
        if (!res.ok || !data || data.ok === false) {
          var err = new Error((data && data.error && data.error.message) || ("HTTP " + res.status));
          err.status = res.status;
          err.payload = data;
          err.code = (data && data.error && data.error.code) || ("http_" + res.status);
          err.details = (data && data.error && data.error.details) || [];
          throw err;
        }
        return data;
      });
    });
  }

  /* --------------------------------------------------------- 5. data load */

  function loadData(opts) {
    var keepView = !(opts && opts.reset);
    setConn("saving", "loading…");
    return api("/api/data").then(function (data) {
      ingest(data);
      if (!keepView) resetViewState();
      buildFilterControls();
      buildTypePalette();
      buildMap();
      renderBanner();
      renderAll();
      renderOrphans();
      renderSaveControls();
      setConn("ok", "connected");
      state.dataError = false;
      checkContract(data.contract);
      surfaceServerWarnings(data.warnings);
      return data;
    }).catch(function (err) {
      state.dataError = true;
      setConn("error", "offline");
      toast("Could not load data: " + err.message, "error");
      throw err;
    });
  }

  function ingest(data) {
    state.loaded = true;
    state.contract = data.contract || CONTRACT_VERSION;
    state.baseToken = data.base_token;
    state.inventoryToken = data.inventory_token;
    state.meta = data.meta || {};
    state.types = (data.types || []).slice();
    state.typeByCode = new Map(state.types.map(function (t) { return [t.code, t]; }));
    state.ownershipCategories = (data.ownership_categories || []).slice();
    state.presentUseValues = (data.present_use_values || []).slice();
    state.drivewayDisplay = data.driveway_display || null;
    state.districts = (data.districts || []).slice();
    state.maindotClasses = (data.maindot_classes || []).slice();
    state.view = data.view || null;
    state.segments = (data.segments || []).slice();
    state.segById = new Map(state.segments.map(function (s) { return [s.id, s]; }));
    state.roads = (data.roads || []).slice();
    state.roadByKey = new Map(state.roads.map(function (r) { return [r.road_key, r]; }));
    state.orphans = (data.orphan_overrides || []).slice();
    state.counts = data.counts || {};
    state.warnings = (data.warnings || []).slice();

    /* Derive anything the server chose not to send, rather than hard-coding it. */
    if (!state.districts.length) {
      var dset = new Set();
      state.segments.forEach(function (s) { (s.districts || []).forEach(function (d) { dset.add(d); }); });
      state.districts = Array.from(dset).sort();
    }
    if (!state.maindotClasses.length) {
      var mset = new Set();
      state.segments.forEach(function (s) { if (s.maindot) mset.add(s.maindot); });
      state.maindotClasses = Array.from(mset).sort();
    }
    /* Drop selections/focus that no longer exist (e.g. a segment was excluded). */
    Array.from(state.selection).forEach(function (id) {
      if (!state.segById.has(id)) state.selection.delete(id);
    });
    if (state.focusId && !state.segById.has(state.focusId)) state.focusId = null;
    if (state.anchorId && !state.segById.has(state.anchorId)) state.anchorId = null;

    /* Bring back anything staged before a reload/crash — only ever into an
       empty pending set, and only when the file it was staged against is still
       what is on disk (checked inside restorePending). */
    invalidateOdd();
    if (!state.pending.size) restorePending();
  }

  function resetViewState() {
    state.filters = { search: "", type: "", family: "", district: "", ownership: "", use: "", override: "", pendingOnly: false };
    state.selection.clear();
    state.collapsedRoads.clear();
    state.focusId = null;
    state.anchorId = null;
    state.zoom = { k: 1, tx: 0, ty: 0 };
  }

  function checkContract(serverContract) {
    var mine = CONTRACT_VERSION.split(".")[0];
    var theirs = String(serverContract || "").split(".")[0];
    if (theirs && theirs !== mine) {
      showBlocking("This page speaks contract " + CONTRACT_VERSION + " but the server speaks " +
        serverContract + ". Saving is disabled until both sides match — reload after restarting serve.py.");
      state.contractMismatch = true;
      renderSaveControls();
    }
  }

  function surfaceServerWarnings(warnings) {
    (warnings || []).forEach(function (w) {
      var level = w.code === "override_drift" || w.code === "orphan_override" ? "warn" : "info";
      var ids = (w.ids || []).slice(0, 4).join(", ");
      toast(w.message + (ids ? " (" + ids + (w.ids.length > 4 ? ", …" : "") + ")" : ""), level);
    });
  }

  /* -------------------------------------------------- 6. filtering + sort */

  function segHaystack(seg) {
    if (seg.__hay === undefined) {
      seg.__hay = fold([
        seg.name, seg.id,
        (seg.termini && seg.termini[0]) || "",
        (seg.termini && seg.termini[1]) || "",
        (seg.override && seg.override.note) || ""
      ].join(" \u0000 "));
    }
    return seg.__hay;
  }

  function passesFilters(seg) {
    var f = state.filters;
    if (f.search && segHaystack(seg).indexOf(f.search) === -1) return false;

    if (f.type) {
      var t = effType(seg);
      if (f.type === "__none__") { if (t) return false; }
      else if (t !== f.type) return false;
    }
    if (f.family) {
      var ft = effType(seg);
      if (!ft || ft.charAt(0) !== f.family) return false;
    }
    if (f.district) {
      if (!(seg.districts || []).some(function (d) { return d === f.district; })) return false;
    }
    if (f.ownership) {
      var ow = effOwnership(seg);
      if (f.ownership === "__blank__") { if (ow) return false; }
      else if (ow !== f.ownership) return false;
    }
    if (f.use) {
      var pu = effPresentUse(seg);
      if (f.use === "__blank__") { if (pu) return false; }
      else if (pu !== f.use) return false;
    }
    if (f.override) {
      switch (f.override) {
        case "has": if (!seg.has_override) return false; break;
        case "none": if (seg.has_override) return false; break;
        case "typed": if (!(seg.override && seg.override.type)) return false; break;
        case "noteonly": if (!isNoteOnly(seg)) return false; break;
        case "excluded": if (!effExcluded(seg)) return false; break;
        case "drift": if (!isDrift(seg)) return false; break;
        case "odd": if (!oddOneOutSet().has(seg.id)) return false; break;
      }
    }
    if (f.pendingOnly && !state.pending.has(seg.id)) return false;
    return true;
  }

  function roadSortValue(road, segs, key) {
    switch (key) {
      case "length": return roadLength(road);
      case "type": {
        var idxs = segs.map(function (s) { return effType(s) ? typeIndex(effType(s)) : 98; });
        return Math.min.apply(null, idxs.length ? idxs : [99]);
      }
      case "ownership": {
        var owns = uniq(segs.map(effOwnership));
        return owns.length === 1 ? (owns[0] || "\uffff") : "mixed";
      }
      case "district": {
        var d = segs.length && segs[0].districts && segs[0].districts.length ? segs[0].districts[0] : "\uffff";
        return d;
      }
      case "use": {
        var uses = uniq(segs.map(effPresentUse));
        return uses.length === 1 ? (uses[0] || "\uffff") : "mixed";
      }
      case "homes": {
        // Sum across the road's segments: a road is a driveway candidate on its
        // whole length, not segment by segment.
        return segs.reduce(function (a, s) {
          return a + ((s.addresses && s.addresses.residential) || 0);
        }, 0);
      }
      case "termini": return fold((segs.length && segs[0].termini && segs[0].termini[0]) || "");
      case "source": return segs.filter(function (s) { return s.has_override; }).length;
      case "name":
      default: return fold(road.name);
    }
  }

  function uniq(arr) {
    var out = [], seen = new Set();
    arr.forEach(function (v) { var k = String(v); if (!seen.has(k)) { seen.add(k); out.push(v); } });
    return out;
  }

  /* Groups roads, applies filters, applies the road-level sort.
     Segments inside a road are ALWAYS ordered by seq (§8.3.2). */
  function computeVisible() {
    var byRoad = new Map();
    for (var i = 0; i < state.segments.length; i++) {
      var seg = state.segments[i];
      if (!passesFilters(seg)) continue;
      var list = byRoad.get(seg.road_key);
      if (!list) { list = []; byRoad.set(seg.road_key, list); }
      list.push(seg);
    }
    var groups = [];
    byRoad.forEach(function (segs, key) {
      segs.sort(function (a, b) { return a.seq - b.seq; });
      var road = state.roadByKey.get(key) || {
        road_key: key, name: segs[0].name,
        segment_ids: segs.map(function (s) { return s.id; }), n: segs.length
      };
      groups.push({ road: road, segs: segs });
    });

    var key = state.sort.key, dir = state.sort.dir === "desc" ? -1 : 1;
    groups.forEach(function (g) { g.__sv = roadSortValue(g.road, g.segs, key); });
    groups.sort(function (a, b) {
      var x = a.__sv, y = b.__sv, c;
      if (typeof x === "number" && typeof y === "number") c = x - y;
      else c = String(x).localeCompare(String(y));
      if (c === 0) c = fold(a.road.name).localeCompare(fold(b.road.name));
      return c * dir;
    });

    state.visibleIds = [];
    state.navIds = [];
    state.visibleRoadKeys = groups.map(function (g) { return g.road.road_key; });
    groups.forEach(function (g) {
      var collapsed = state.collapsedRoads.has(g.road.road_key);
      g.segs.forEach(function (s) {
        state.visibleIds.push(s.id);
        if (!collapsed) state.navIds.push(s.id);
      });
    });
    state.visibleSet = new Set(state.visibleIds);
    return groups;
  }

  /* ------------------------------------------------------ 7. table render */

  function fillOptions(select, items, opts) {
    if (!select) return;
    var keep = select.value;
    select.textContent = "";
    (items || []).forEach(function (it) {
      var o = document.createElement("option");
      o.value = it.value;
      o.textContent = it.label;
      if (it.title) o.title = it.title;
      select.appendChild(o);
    });
    if (opts && opts.value !== undefined) select.value = opts.value;
    else if (keep) select.value = keep;
  }

  /* `compact` = bare codes ("S1"). The in-row Type controls are ~76 px wide, so a
     full "S1 — Main Street" label renders as an unreadable ellipsis and the current
     Type — the whole point of the column — becomes invisible. Bare codes fit; the
     full name stays on the option's tooltip, on the row swatch, and in the
     inspector. Wide controls (filter, palette, dialogs) keep the long labels. */
  function typeOptionList(placeholder, compact) {
    var out = [{ value: "", label: placeholder }];
    state.types.forEach(function (t) {
      out.push({
        value: t.code,
        label: compact ? t.code : t.code + " — " + t.name,
        title: t.code + " — " + t.name
      });
    });
    return out;
  }
  function ownershipOptionList(placeholder, blankLabel) {
    var out = [{ value: "", label: placeholder }];
    state.ownershipCategories.forEach(function (o) { out.push({ value: o, label: o }); });
    if (blankLabel) out.push({ value: "__blank__", label: blankLabel });
    return out;
  }

  function presentUseOptionList(placeholder, blankLabel) {
    var out = [{ value: "", label: placeholder }];
    state.presentUseValues.forEach(function (v) {
      out.push({ value: v, label: v === "Driveway" ? "Driveway (D)" : v });
    });
    if (blankLabel) out.push({ value: "__blank__", label: blankLabel });
    return out;
  }
  /* Map/swatch colour: a segment recorded as a driveway today reads as D, not as
     the Road Type it would become on conversion. Exhibit 3.1 does the same. */
  function drivewayColor() {
    return (state.drivewayDisplay && state.drivewayDisplay.color) || "#A2988C";
  }
  function segColor(seg) {
    return isDriveway(seg) ? drivewayColor() : typeColor(effType(seg));
  }

  function tplNode(id, sel) {
    var t = E(id);
    if (!t || !t.content) return null;
    var frag = t.content.cloneNode(true);
    return sel ? frag.querySelector(sel) : frag.firstElementChild;
  }

  function segRowProto() {
    if (!protos.segRow) {
      var row = tplNode("tpl-segment-row", "tr.segment-row") || tplNode("tpl-segment-row");
      if (!row) return null;
      fillOptions(qs(row, ".seg-type-select"), typeOptionList("—", true), { value: "" });
      fillOptions(qs(row, ".seg-ownership-select"), ownershipOptionList("—"), { value: "" });
      fillOptions(qs(row, ".seg-use-select"), presentUseOptionList("—"), { value: "" });
      protos.segRow = row;
    }
    return protos.segRow.cloneNode(true);
  }
  function roadRowProto() {
    if (!protos.roadRow) {
      var row = tplNode("tpl-road-row", "tr.road-row") || tplNode("tpl-road-row");
      if (!row) return null;
      fillOptions(qs(row, ".road-type-select"), typeOptionList("Set road…", true), { value: "" });
      protos.roadRow = row;
    }
    return protos.roadRow.cloneNode(true);
  }

  function renderAll() {
    var tbody = E("segment-tbody");
    if (!tbody) return;
    var groups = computeVisible();
    var frag = document.createDocumentFragment();
    state.rowById = new Map();
    state.roadRowByKey = new Map();

    groups.forEach(function (g) {
      var rr = buildRoadRow(g.road, g.segs);
      if (rr) { frag.appendChild(rr); state.roadRowByKey.set(g.road.road_key, rr); }
      g.segs.forEach(function (seg) {
        var row = buildSegmentRow(seg);
        if (!row) return;
        frag.appendChild(row);
        state.rowById.set(seg.id, row);
      });
    });

    tbody.textContent = "";
    tbody.appendChild(frag);

    var table = E("segment-table");
    if (table) table.setAttribute("aria-rowcount", String(state.visibleIds.length + groups.length + 1));
    setHidden(E("empty-state"), state.visibleIds.length > 0);

    /* row state (classes, selects, swatches) after the nodes are in the DOM */
    state.rowById.forEach(function (_row, id) { renderRowState(id); });
    state.roadRowByKey.forEach(function (_row, key) { renderRoadRowState(key); });

    renderSortIndicators();
    renderResultCount(groups.length);
    renderSelectionBar();
    renderSummary();
    renderLegend();
    applyMapFilterClasses();
    renderMapSelection();
    renderDetail();
    renderPending();
    updateSelectAllState();
  }

  function buildRoadRow(road, segs) {
    var row = roadRowProto();
    if (!row) return null;
    row.dataset.roadKey = road.road_key;
    setText(row, ".road-name", road.name);
    setText(row, ".road-count", segs.length + " of " + (road.n || segs.length) + " " + plural(road.n || segs.length, "segment"));
    var zoomBtn = qs(row, ".road-zoom");
    if (zoomBtn && !zoomBtn.getAttribute("aria-label")) zoomBtn.setAttribute("aria-label", "Show " + road.name + " on the map");
    var chk = qs(row, ".road-check");
    if (chk) chk.setAttribute("aria-label", "Select all of " + road.name);
    return row;
  }

  function renderRoadRowState(roadKey) {
    var row = state.roadRowByKey.get(roadKey);
    if (!row) return;
    var road = state.roadByKey.get(roadKey);
    var allIds = road ? road.segment_ids : [];
    var visIds = allIds.filter(function (id) { return state.visibleSet.has(id); });
    var segs = visIds.map(function (id) { return state.segById.get(id); }).filter(Boolean);
    var allSegs = allIds.map(function (id) { return state.segById.get(id); }).filter(Boolean);

    /* types present (effective) */
    var codes = sortTypeCodes(uniq(allSegs.map(effType).filter(Boolean)));
    var holder = qs(row, ".road-types");
    if (holder) {
      holder.textContent = "";
      codes.forEach(function (c) {
        var pill = document.createElement("span");
        pill.className = "type-pill";
        pill.dataset.type = c;
        pill.style.setProperty("--pill-color", typeColor(c));
        pill.style.backgroundColor = typeColor(c);
        pill.textContent = c;
        pill.title = typeLabel(c);
        holder.appendChild(pill);
      });
      if (!codes.length) {
        var none = document.createElement("span");
        none.className = "type-pill";
        none.dataset.type = "";
        none.textContent = "—";
        holder.appendChild(none);
      }
    }
    row.classList.toggle("is-mixed", codes.length > 1);

    var ovCount = allSegs.filter(function (s) { return s.has_override; }).length;
    var flag = qs(row, ".road-flag-override");
    if (flag) {
      flag.textContent = ovCount ? ovCount + " overridden" : "";
      flag.hidden = ovCount === 0;
    }
    setText(row, ".road-length", fmtFt(allSegs.reduce(function (a, s) { return a + segLength(s); }, 0)));

    var owns = uniq(allSegs.map(effOwnership));
    setText(row, ".road-ownership", owns.length === 1 ? (owns[0] || "—") : "mixed");

    /* The two whole-road controls in this row have different scopes on purpose:
       the checkbox selects what you can see, the Type select sets the road. Ben
       works in whole roads ("all of Main Street is S1") and the generated note
       says "for its full length", so the select must not quietly mean "the six
       of nine you happen to be looking at". Say which is which, in the row. */
    var hiddenN = allIds.length - visIds.length;
    setText(row, ".road-count", visIds.length + " of " + allIds.length + " " +
      plural(allIds.length, "segment") + (hiddenN ? " shown · Type sets all " + allIds.length : ""));
    row.classList.toggle("is-partly-filtered", hiddenN > 0);
    var tsel = qs(row, ".road-type-select");
    if (tsel) {
      tsel.title = "Set the Type for all " + allIds.length + " " + plural(allIds.length, "segment") +
        " of " + (road ? road.name : "this road") +
        (hiddenN ? " — including the " + hiddenN + " hidden by the current filter" : "") +
        ". The checkbox beside it selects only the visible ones.";
    }

    row.classList.toggle("is-collapsed", state.collapsedRoads.has(roadKey));
    var toggle = qs(row, ".road-toggle");
    if (toggle) {
      var expanded = !state.collapsedRoads.has(roadKey);
      toggle.setAttribute("aria-expanded", String(expanded));
      toggle.textContent = expanded ? "▾" : "▸";
    }
    var pendingCount = allIds.filter(function (id) { return state.pending.has(id); }).length;
    row.classList.toggle("is-pending", pendingCount > 0);

    var chk = qs(row, ".road-check");
    if (chk) {
      var sel = visIds.filter(function (id) { return state.selection.has(id); }).length;
      chk.checked = visIds.length > 0 && sel === visIds.length;
      chk.indeterminate = sel > 0 && sel < visIds.length;
    }
  }

  function buildSegmentRow(seg) {
    var row = segRowProto();
    if (!row) return null;
    row.dataset.id = seg.id;
    row.dataset.roadKey = seg.road_key;
    row.dataset.seq = String(seg.seq);
    setText(row, ".seg-name", seg.name);
    setText(row, ".seg-seq", "#" + seg.seq);
    setText(row, ".seg-id", seg.id);
    setText(row, ".seg-from", (seg.termini && seg.termini[0]) || "—");
    setText(row, ".seg-to", (seg.termini && seg.termini[1]) || "—");
    setText(row, ".seg-length", fmtFt(segLength(seg)));
    // Homes: the Art 3 §7.C.7 driveway threshold as decision support. The
    // unknown-type count is shown ALONGSIDE, never folded in -- 311 of the
    // town's 1227 address points carry no PLACE_TYPE, so "0" and "0 (+2?)"
    // are different situations and must not look the same.
    var addr = seg.addresses || { residential: 0, unknown_type: 0, total: 0 };
    setText(row, ".seg-homes", String(addr.residential || 0));
    var unkEl = qs(row, ".seg-homes-unk");
    if (unkEl) {
      unkEl.textContent = addr.unknown_type ? " +" + addr.unknown_type + "?" : "";
      unkEl.title = addr.unknown_type
        ? addr.unknown_type + " address point(s) here carry no PLACE_TYPE — unreviewed, not absent"
        : "";
    }
    row.classList.toggle("is-at-threshold",
      (addr.residential || 0) <= 2 && seg.ownership === "Private Road");
    var chk = qs(row, ".seg-check");
    if (chk) chk.setAttribute("aria-label", "Select " + seg.name + " #" + seg.seq);
    var noteBtn = qs(row, ".seg-note-btn");
    if (noteBtn) noteBtn.setAttribute("aria-label", "Edit note for " + seg.id);
    var detBtn = qs(row, ".seg-detail-btn");
    if (detBtn) detBtn.setAttribute("aria-label", "Inspect " + seg.id);
    var exBtn = qs(row, ".seg-exclude-btn");
    if (exBtn) exBtn.setAttribute("aria-label", "Exclude " + seg.id + " from the inventory");
    if (!row.hasAttribute("tabindex")) row.setAttribute("tabindex", "-1");
    row.hidden = state.collapsedRoads.has(seg.road_key);
    return row;
  }

  /* Mutates only the nodes of one row (§9.4) — never a full re-render. */
  function renderRowState(id) {
    var row = state.rowById.get(id);
    var seg = state.segById.get(id);
    if (!row || !seg) return;
    var pc = state.pending.get(id);
    var t = effType(seg);

    row.classList.toggle("is-selected", state.selection.has(id));
    row.classList.toggle("is-focused", state.focusId === id);
    row.classList.toggle("is-pending", !!pc);
    row.classList.toggle("is-hovered", state.hoverId === id);
    row.classList.toggle("has-override", !!seg.has_override);
    row.classList.toggle("is-note-only", isNoteOnly(seg));
    row.classList.toggle("is-excluded", effExcluded(seg));
    row.classList.toggle("is-drift", isDrift(seg));
    row.classList.toggle("is-blank-ownership", !effOwnership(seg));
    row.classList.toggle("is-delete", !!pc && pc.kind === "delete");

    var chk = qs(row, ".seg-check");
    if (chk) chk.checked = state.selection.has(id);

    var sel = qs(row, ".seg-type-select");
    if (sel && sel.value !== t) sel.value = t;
    var sw = qs(row, ".type-swatch");
    if (sw) {
      sw.style.backgroundColor = t ? typeColor(t) : TYPE_NONE_COLOR;
      sw.title = typeLabel(t);
    }

    /* pending type shown as old → new inside the cell (§8.3.4) */
    var cell = qs(row, ".cell-type");
    if (cell) {
      var changed = !!(pc && pc.kind === "set" && hasOwn(pc.fields, "type"));
      cell.classList.toggle("is-changed", changed);
      var was = qs(cell, ".seg-type-was");
      if (changed) {
        if (!was) {
          was = document.createElement("span");
          was.className = "seg-type-was";
          cell.insertBefore(was, cell.firstChild);
        }
        var from = pc.fields.type.from;
        was.textContent = (from || "—") + " →";
        was.title = "was " + typeLabel(from);
      } else if (was) {
        was.remove();
      }
    }

    /* Flag the segment that disagrees with the rest of its own road. */
    var odd = oddOneOutSet().has(id);
    row.classList.toggle("is-odd-type", odd);
    var cellT = qs(row, ".cell-type");
    if (cellT) {
      var mark = qs(cellT, ".seg-odd-flag");
      if (odd) {
        if (!mark) {
          mark = document.createElement("span");
          mark.className = "seg-odd-flag";
          mark.textContent = "⚠";
          cellT.appendChild(mark);
        }
        var maj = oddMajorityType(seg);
        mark.title = "The rest of " + seg.name + " is " + (maj || "untyped") +
          "; this segment is " + (t || "untyped") + ". Worth checking against the map.";
      } else if (mark) {
        mark.remove();
      }
    }

    var own = qs(row, ".seg-ownership-select");
    if (own) {
      var ov = effOwnership(seg);
      if (own.value !== ov) own.value = ov;
    }

    var use = qs(row, ".seg-use-select");
    if (use) {
      var uv = effPresentUse(seg);
      if (use.value !== uv) use.value = uv;
    }
    row.classList.toggle("is-driveway", isDriveway(seg));

    var src = qs(row, ".seg-source");
    if (src) {
      var source = pc ? "pending" : (seg.type_source || "auto");
      src.dataset.source = source;
      src.textContent = source === "override" ? "Override"
        : source === "pending" ? "Pending" : "Auto";
      src.title = source === "override"
        ? "Type comes from overrides.json (always wins over auto-classification)"
        : source === "pending" ? "Staged, not yet saved" : "Auto-classified by the GIS pipeline";
    }
  }

  function renderSortIndicators() {
    var head = E("segment-head");
    if (!head) return;
    qsa(head, "th[data-sort]").forEach(function (th) {
      var active = th.dataset.sort === state.sort.key;
      th.classList.toggle("is-sorted", active);
      if (active) th.dataset.dir = state.sort.dir;
      else delete th.dataset.dir;
      th.setAttribute("aria-sort", active ? (state.sort.dir === "asc" ? "ascending" : "descending") : "none");
    });
  }

  function renderResultCount(roadCount) {
    var n = state.visibleIds.length;
    var total = state.segments.length;
    setText(document, "#filter-result-count",
      "Showing " + fmtInt(n) + " of " + fmtInt(total) + " " + plural(total, "segment") +
      " in " + fmtInt(roadCount) + " " + plural(roadCount, "road"));
  }

  /* ------------------------------------------------- 8. summary + legend */

  function computeEffectiveTypeCounts() {
    var by = {};
    state.types.forEach(function (t) { by[t.code] = 0; });
    by[""] = 0;
    state.segments.forEach(function (s) {
      if (effExcluded(s)) return;                     // an excluded segment leaves the inventory
      var t = effType(s);
      if (hasOwn(by, t)) by[t] += 1; else by[t] = 1;
    });
    state.effTypeCount = by;
    return by;
  }

  function renderSummary() {
    var c = state.counts || {};
    var by = computeEffectiveTypeCounts();
    /* Every headline number is "what the file will hold after Save", so a staged
       DELETE has to subtract — it removes the whole entry, Type and all. */
    var typedOverrides = state.segments.filter(function (s) {
      var pc = state.pending.get(s.id);
      if (pc && pc.kind === "delete") return false;
      if (pc && pc.kind === "set" && hasOwn(pc.fields, "type")) return pc.fields.type.to !== null;
      return !!(s.override && s.override.type);
    }).length;
    /* excluded = entries on disk ± what is staged (an exclusion may target an
       orphan, so start from the server count rather than recounting segments) */
    var exDelta = 0;
    state.pending.forEach(function (pc) {
      if (pc.kind === "delete") {
        var ds = state.segById.get(pc.id);
        if (ds && ds.excluded === true) exDelta -= 1;
        else if (!ds) {
          var orph = state.orphans.filter(function (o) { return o.id === pc.id; })[0];
          if (orph && orph.entry && orph.entry.exclude === true) exDelta -= 1;
        }
        return;
      }
      if (pc.kind !== "set" || !hasOwn(pc.fields, "exclude")) return;
      exDelta += pc.fields.exclude.to === true ? 1 : -1;
    });
    var excluded = Math.max(0, (c.override_excluded || 0) + exDelta);

    /* An OPEN ITEM stops being one when it is deleted or given a real value. */
    var noteOnly = c.override_note_only || 0;
    state.pending.forEach(function (pc) {
      var s = state.segById.get(pc.id);
      if (!s || !isNoteOnly(s)) return;
      if (pc.kind === "delete") { noteOnly -= 1; return; }
      var gains = FIELD_ORDER.some(function (f) {
        return hasOwn(pc.fields, f) && pc.fields[f].to !== null && pc.fields[f].to !== false;
      });
      if (gains) noteOnly -= 1;
    });
    noteOnly = Math.max(0, noteOnly);

    setText(document, "#summary-total", fmtInt(c.segments != null ? c.segments : state.segments.length) + " segments");
    setText(document, "#summary-roads", fmtInt(c.roads != null ? c.roads : state.roadByKey.size) + " roads");
    setText(document, "#summary-overrides", fmtInt(typedOverrides) + " Type overrides");
    setText(document, "#summary-noteonly", fmtInt(noteOnly) + " open " + plural(noteOnly, "item"));
    setText(document, "#summary-excluded", fmtInt(excluded) + " excluded");

    var p = state.pending.size;
    var pendEl = E("summary-pending");
    if (pendEl) {
      pendEl.textContent = fmtInt(p) + " pending";
      pendEl.classList.toggle("is-active", p > 0);
    }

    /* Live count on the filter option — the point of the flag is to be found. */
    var oddSel = E("filter-override");
    if (oddSel) {
      var n = oddOneOutSet().size;
      qsa(oddSel, "option").forEach(function (o) {
        if (o.value === "odd") o.textContent = "Differs from its road" + (n ? " (" + n + ")" : "");
      });
    }

    var host = E("summary-types");
    if (host) {
      host.textContent = "";
      var frag = document.createDocumentFragment();
      state.types.forEach(function (t) {
        var chip = tplNode("tpl-type-chip", ".type-chip") || tplNode("tpl-type-chip");
        if (!chip) return;
        chip.dataset.type = t.code;
        var sw = qs(chip, ".type-chip-swatch");
        if (sw) sw.style.backgroundColor = t.color;
        setText(chip, ".type-chip-code", t.code);
        setText(chip, ".type-chip-count", fmtInt(by[t.code] || 0));
        chip.classList.toggle("is-empty", !by[t.code]);
        chip.title = typeLabel(t.code) + " — " + fmtInt(by[t.code] || 0) + " segments (click to filter)";
        frag.appendChild(chip);
      });
      host.appendChild(frag);
    }
  }

  function renderLegend() {
    var host = E("map-legend");
    if (!host) return;
    var by = state.effTypeCount && Object.keys(state.effTypeCount).length ? state.effTypeCount : computeEffectiveTypeCounts();
    host.textContent = "";
    var frag = document.createDocumentFragment();
    state.types.forEach(function (t) {
      if (!by[t.code]) return;                       // legends show only Types present
      var item = tplNode("tpl-legend-item", ".legend-item") || tplNode("tpl-legend-item");
      if (!item) return;
      item.dataset.type = t.code;
      var sw = qs(item, ".legend-swatch");
      if (sw) sw.style.backgroundColor = t.color;
      setText(item, ".legend-code", t.code);
      setText(item, ".legend-name", t.name);
      setText(item, ".legend-count", fmtInt(by[t.code]));
      item.title = "Filter to " + typeLabel(t.code);
      frag.appendChild(item);
    });

    /* Driveways (present use) are their own legend row, appended after the Types
       and shown only once at least one segment is marked. They are not a Type:
       each still carries the Type it would take on conversion (Art 3 §7.F). */
    var nDrive = 0;
    state.segments.forEach(function (sg) { if (isDriveway(sg)) nDrive++; });
    if (nDrive) {
      var d = state.drivewayDisplay || { code: "D", name: "Driveway (present use)" };
      var ditem = tplNode("tpl-legend-item", ".legend-item") || tplNode("tpl-legend-item");
      if (ditem) {
        ditem.dataset.type = "D";
        var dsw = qs(ditem, ".legend-swatch");
        if (dsw) dsw.style.backgroundColor = drivewayColor();
        setText(ditem, ".legend-code", d.code);
        setText(ditem, ".legend-name", d.name);
        setText(ditem, ".legend-count", fmtInt(nDrive));
        ditem.title = "Filter to segments recorded as driveways today";
        frag.appendChild(ditem);
      }
    }

    host.appendChild(frag);
  }

  function renderBanner() {
    var b = E("data-banner");
    if (!b) return;
    var text = state.meta && state.meta.banner ? state.meta.banner : "";
    b.textContent = text;
    b.hidden = !text;
  }

  /* ---------------------------------------------------------- 9. the map */

  function projectPoint(x, y) {
    var v = state.view;
    if (!v) return [0, 0];
    return [v.offx + (x - v.minx) * v.scale, v.offy + (v.maxy - y) * v.scale];
  }

  function buildMap() {
    var svg = E("map");
    var lines = E("map-lines");
    if (!svg || !lines) return;
    var v = state.view;
    if (v) svg.setAttribute("viewBox", "0 0 " + v.vbw + " " + v.vbh);

    lines.textContent = "";
    var hits = E("map-hits");
    if (hits) hits.textContent = "";
    state.pathById = new Map();
    state.titleById = new Map();
    var frag = document.createDocumentFragment();
    var hitFrag = document.createDocumentFragment();

    state.segments.forEach(function (seg) {
      var d = seg.path || pathFromGeometry(seg.geometry);
      if (!d) return;                                 // degenerate geometry: table only (§11.1)
      var p = document.createElementNS(SVG_NS, "path");
      p.setAttribute("class", "map-seg");
      p.setAttribute("d", d);
      p.setAttribute("fill", "none");
      p.setAttribute("stroke", segColor(seg));
      p.setAttribute("stroke-linecap", "round");
      p.setAttribute("stroke-linejoin", "round");
      p.setAttribute("vector-effect", "non-scaling-stroke");
      p.dataset.id = seg.id;
      p.dataset.roadKey = seg.road_key;
      p.dataset.type = effType(seg);
      var title = document.createElementNS(SVG_NS, "title");
      title.textContent = segTitle(seg);
      p.appendChild(title);
      frag.appendChild(p);
      state.pathById.set(seg.id, p);
      state.titleById.set(seg.id, title);

      /* A transparent fat twin so a 745 ft stub is hoverable and clickable
         without drawing it heavier than it is. */
      if (hits) {
        var h = document.createElementNS(SVG_NS, "path");
        h.setAttribute("class", "map-hit");
        h.setAttribute("d", d);
        h.dataset.id = seg.id;
        h.dataset.roadKey = seg.road_key;
        hitFrag.appendChild(h);
      }
    });
    lines.appendChild(frag);
    if (hits) hits.appendChild(hitFrag);
    applyZoom();
  }

  function pathFromGeometry(geom) {
    if (!geom || geom.length < 2) return "";
    var out = "", i;
    for (i = 0; i < geom.length; i++) {
      var pt = projectPoint(geom[i][0], geom[i][1]);
      out += (i ? "L" : "M") + round2(pt[0]) + " " + round2(pt[1]);
    }
    return out;
  }
  function round2(v) { return Math.round(v * 100) / 100; }

  function renderMapState(id) {
    var p = state.pathById.get(id);
    var seg = state.segById.get(id);
    if (!p || !seg) return;
    var pc = state.pending.get(id);
    var t = isDriveway(seg) ? "D" : effType(seg);
    if (p.dataset.type !== t) {
      p.dataset.type = t;
      p.setAttribute("stroke", segColor(seg));
    }
    p.classList.toggle("is-selected", state.selection.has(id));
    p.classList.toggle("is-hovered", state.hoverId === id);
    p.classList.toggle("is-pending", !!pc);
    p.classList.toggle("is-excluded", effExcluded(seg));
    var title = state.titleById.get(id);
    if (title) title.textContent = segTitle(seg);
  }

  function applyMapFilterClasses() {
    var dim = state.dimFiltered;
    toggleClass(E("map"), "is-dimming", dim);
    state.pathById.forEach(function (p, id) {
      /* Only apply the class when dimming is on, so the checkbox works
         regardless of how styles.css chose to express the rule. */
      p.classList.toggle("is-filtered-out", dim && !state.visibleSet.has(id));
    });
  }

  function makeHalo(id, cls) {
    var src = state.pathById.get(id);
    if (!src) return null;
    var h = document.createElementNS(SVG_NS, "path");
    h.setAttribute("class", cls);
    h.setAttribute("d", src.getAttribute("d"));
    h.setAttribute("fill", "none");
    h.setAttribute("stroke", src.getAttribute("stroke"));
    h.setAttribute("stroke-width", "9");
    h.setAttribute("stroke-opacity", "0.28");
    h.setAttribute("stroke-linecap", "round");
    h.setAttribute("stroke-linejoin", "round");
    h.setAttribute("vector-effect", "non-scaling-stroke");
    h.dataset.id = id;
    return h;
  }

  /* Halo = a wider, low-opacity duplicate under the selection (§8.4.1). */
  function renderMapSelection() {
    var halo = E("map-halo");
    state.pathById.forEach(function (p, id) {
      p.classList.toggle("is-selected", state.selection.has(id));
    });
    if (!halo) return;
    halo.textContent = "";
    var frag = document.createDocumentFragment();
    state.selection.forEach(function (id) {
      var h = makeHalo(id, "map-halo-seg");
      if (h) frag.appendChild(h);
    });
    halo.appendChild(frag);
    renderHoverHalo();
  }

  /* Thickening a 277 ft lane from 1.9 to 3.2 px is invisible at town scale, so
     a hovered row gets the same halo the selection does. */
  function renderHoverHalo() {
    var halo = E("map-halo");
    if (!halo) return;
    var old = halo.querySelector(".map-halo-hover");
    if (old) old.remove();
    var id = state.hoverId;
    if (!id || state.selection.has(id)) return;
    var h = makeHalo(id, "map-halo-seg map-halo-hover");
    if (h) halo.appendChild(h);
  }

  function renderMapMarkers() {
    var host = E("map-markers");
    if (!host) return;
    host.textContent = "";
    var seg = state.focusId ? state.segById.get(state.focusId) : null;
    if (!seg || !seg.mid) return;
    var c = document.createElementNS(SVG_NS, "circle");
    c.setAttribute("class", "map-mid");
    c.setAttribute("cx", String(seg.mid[0]));
    c.setAttribute("cy", String(seg.mid[1]));
    c.setAttribute("r", "4.5");
    c.setAttribute("fill", segColor(seg));
    c.setAttribute("stroke", "#FFFFFF");
    c.setAttribute("stroke-width", "1.5");
    c.setAttribute("vector-effect", "non-scaling-stroke");
    c.dataset.id = seg.id;
    host.appendChild(c);
  }

  /* hover: rAF-throttled, touches exactly two nodes (§8.4.1) */
  var hoverQueued = null, hoverRaf = 0;

  function flushHover() {
    hoverRaf = 0;
    var q = hoverQueued; hoverQueued = null;
    if (!q) return;
    var prev = state.hoverId;
    if (prev === q.id) return;
    state.hoverId = q.id;
    if (prev) {
      var pr = state.rowById.get(prev); if (pr) pr.classList.remove("is-hovered");
      var pp = state.pathById.get(prev); if (pp) pp.classList.remove("is-hovered");
    }
    var label = E("map-hover-label");
    if (q.id) {
      var r = state.rowById.get(q.id); if (r) r.classList.add("is-hovered");
      var p = state.pathById.get(q.id); if (p) p.classList.add("is-hovered");
      var seg = state.segById.get(q.id);
      if (label && seg) label.textContent = segTitle(seg);
      if (q.scroll && r) scrollRowIntoView(r);
    } else if (label) {
      label.textContent = "";
    }
    renderHoverHalo();
  }

  function setHover(id, opts) {
    if (state.hoverId === id && hoverQueued === null) return;
    hoverQueued = { id: id, scroll: !!(opts && opts.scrollRow) };
    if (hoverRaf) return;
    /* A hidden document never runs rAF callbacks, which would strand the
       queue; apply directly in that case. */
    if (document.hidden) { flushHover(); return; }
    hoverRaf = requestAnimationFrame(flushHover);
  }

  function scrollRowIntoView(row) {
    var panel = E("table-panel") || document.scrollingElement;
    var rr = row.getBoundingClientRect();
    var host = panel === document.scrollingElement
      ? { top: 0, bottom: window.innerHeight }
      : panel.getBoundingClientRect();
    if (rr.top < host.top + 8 || rr.bottom > host.bottom - 8) {
      row.scrollIntoView({ block: "nearest", inline: "nearest" });
    }
  }

  /* zoom / pan */
  function applyZoom() {
    var vp = E("map-viewport");
    if (!vp) return;
    var z = state.zoom;
    vp.setAttribute("transform", "translate(" + round2(z.tx) + " " + round2(z.ty) + ") scale(" + (Math.round(z.k * 1000) / 1000) + ")");
  }
  /* The whole town is ~16,800 ft across a few hundred CSS pixels, so 12x left
     the village core sub-pixel: a 56 ft Main Street segment drew 0.03 px wide
     and could not be clicked. 64x brings the downtown block up to a workable
     size; strokes are non-scaling so lines stay the same weight throughout. */
  function clampK(k) { return Math.min(64, Math.max(1, k)); }
  function zoomAbout(px, py, factor) {
    var z = state.zoom;
    var k2 = clampK(z.k * factor);
    if (k2 === z.k) return;
    z.tx = px - k2 * (px - z.tx) / z.k;
    z.ty = py - k2 * (py - z.ty) / z.k;
    z.k = k2;
    clampPan();
    applyZoom();
  }
  function clampPan() {
    var v = state.view; if (!v) return;
    var z = state.zoom;
    var minTx = v.vbw - v.vbw * z.k, minTy = v.vbh - v.vbh * z.k;
    z.tx = Math.min(0, Math.max(minTx, z.tx));
    z.ty = Math.min(0, Math.max(minTy, z.ty));
  }
  function svgPoint(evt) {
    var svg = E("map");
    if (!svg || !svg.getScreenCTM) return null;
    var ctm = svg.getScreenCTM();
    if (!ctm) return null;
    var pt = svg.createSVGPoint();
    pt.x = evt.clientX; pt.y = evt.clientY;
    var p = pt.matrixTransform(ctm.inverse());
    return [p.x, p.y];
  }
  function resetZoom() { state.zoom = { k: 1, tx: 0, ty: 0 }; applyZoom(); }

  function zoomToIds(ids) {
    var v = state.view;
    if (!v || !ids || !ids.length) return;
    var minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity, any = false;
    ids.forEach(function (id) {
      var seg = state.segById.get(id);
      if (!seg || !seg.geometry) return;
      seg.geometry.forEach(function (pt) {
        var p = projectPoint(pt[0], pt[1]);
        if (p[0] < minx) minx = p[0];
        if (p[0] > maxx) maxx = p[0];
        if (p[1] < miny) miny = p[1];
        if (p[1] > maxy) maxy = p[1];
        any = true;
      });
    });
    if (!any) return;
    var w = Math.max(maxx - minx, 8), h = Math.max(maxy - miny, 8);
    var k = clampK(Math.min(v.vbw / (w * 1.6), v.vbh / (h * 1.6)));
    var cx = (minx + maxx) / 2, cy = (miny + maxy) / 2;
    state.zoom = { k: k, tx: v.vbw / 2 - k * cx, ty: v.vbh / 2 - k * cy };
    clampPan();
    applyZoom();
  }

  /* ------------------------------------------------- 10. detail inspector */

  function renderDetail() {
    var panel = E("detail-panel");
    if (!panel) return;
    var seg = state.focusId ? state.segById.get(state.focusId) : null;
    panel.hidden = !seg;
    renderMapMarkers();
    if (!seg) return;

    var t = effType(seg);
    setText(panel, "#detail-name", seg.name + " #" + seg.seq);
    setText(panel, "#detail-id", seg.id);
    setText(panel, "#detail-termini",
      ((seg.termini && seg.termini[0]) || "—") + " → " + ((seg.termini && seg.termini[1]) || "—"));
    setText(panel, "#detail-length", fmtFt(segLength(seg)) + " (" + fmtMi(segLength(seg)) + ")");

    var typeEl = E("detail-type");
    if (typeEl) {
      typeEl.textContent = "";
      var sw = document.createElement("span");
      sw.className = "type-swatch";
      sw.style.backgroundColor = t ? typeColor(t) : TYPE_NONE_COLOR;
      typeEl.appendChild(sw);
      typeEl.appendChild(document.createTextNode(" " + typeLabel(t)));
      if (state.pending.has(seg.id)) typeEl.classList.add("is-changed");
      else typeEl.classList.remove("is-changed");
    }

    var src = seg.type_source || "auto";
    var srcText = src;
    if (src === "auto" && seg.auto_type) srcText = "auto-classified as " + seg.auto_type;
    else if (src === "override") srcText = "override (the classifier's own value is not recoverable from these files)";
    if (isDrift(seg)) srcText += " · drift: overrides.json says " + seg.override.type + ", the inventory says " + (seg.type || "—");
    setText(panel, "#detail-source", srcText);

    setText(panel, "#detail-ownership", effOwnership(seg) || "not recorded");
    setText(panel, "#detail-districts", (seg.districts || []).join(", ") || "—");
    setText(panel, "#detail-maindot", seg.maindot || "—");

    var noteEl = E("detail-note");
    if (noteEl) {
      /* Show what the entry WILL say, like every other field in this panel —
         a staged note that only appears in the pending list reads as if the
         edit was lost. */
      var pcNote = state.pending.get(seg.id);
      var onDisk = existingNote(seg);
      var staged = pcNote && pcNote.kind !== "delete" && pcNote.note != null ? pcNote.note : null;
      var note = staged != null ? staged : onDisk;
      var deletingNote = !!(pcNote && pcNote.kind === "delete");
      noteEl.textContent = deletingNote
        ? (onDisk ? "entry deletion staged — discards: " + onDisk : "entry deletion staged")
        : (note || "no note");
      noteEl.classList.toggle("is-empty", !deletingNote && !note);
      noteEl.classList.toggle("is-changed", !!staged && staged !== onDisk);
      noteEl.classList.toggle("is-discarded", deletingNote);
      noteEl.title = (staged && onDisk && staged !== onDisk) ? "replaces: " + onDisk : "";
    }

    var rowFt = E("detail-row-ft");
    if (rowFt && document.activeElement !== rowFt) rowFt.value = effective(seg, "row_ft") == null ? "" : effective(seg, "row_ft");
    var trav = E("detail-traveled-ft");
    if (trav && document.activeElement !== trav) trav.value = effective(seg, "traveled_ft") == null ? "" : effective(seg, "traveled_ft");
    var nonc = E("detail-nonconformity");
    if (nonc && document.activeElement !== nonc) nonc.value = effective(seg, "nonconformity") || "";

    var neigh = E("detail-neighbors");
    if (neigh) {
      neigh.textContent = "";
      var road = state.roadByKey.get(seg.road_key);
      var ids = road ? road.segment_ids : [seg.id];
      var frag = document.createDocumentFragment();
      ids.forEach(function (nid) {
        var ns = state.segById.get(nid);
        if (!ns) return;
        var btn = tplNode("tpl-detail-neighbor", ".detail-neighbor") || tplNode("tpl-detail-neighbor");
        if (!btn) {
          btn = document.createElement("button");
          btn.type = "button";
          btn.className = "detail-neighbor";
        }
        btn.dataset.id = nid;
        var nt = effType(ns);
        var labelled = setText(btn, ".neighbor-label", ns.name + " #" + ns.seq + " · " + fmtFt(segLength(ns)));
        var pill = qs(btn, ".type-pill");
        if (pill) {
          pill.dataset.type = nt;
          pill.textContent = nt || "—";
          pill.style.backgroundColor = nt ? typeColor(nt) : TYPE_NONE_COLOR;
        }
        if (!labelled && !pill) {
          btn.textContent = "#" + ns.seq + " " + (nt || "—") + " · " + fmtFt(segLength(ns));
        }
        btn.classList.toggle("is-current", nid === seg.id);
        btn.title = segTitle(ns);
        frag.appendChild(btn);
      });
      neigh.appendChild(frag);
    }

    var raw = E("detail-raw");
    if (raw) {
      if (seg.override) {
        raw.hidden = false;
        raw.textContent = JSON.stringify(seg.override, null, 2);
      } else {
        raw.hidden = true;
        raw.textContent = "";
      }
    }

    var exBtn = E("detail-exclude-btn");
    if (exBtn) {
      var ex = effExcluded(seg);
      exBtn.textContent = ex ? "Un-exclude" : "Exclude from inventory";
      exBtn.classList.toggle("is-danger", !ex);
    }

    /* Only offered when there is an entry to remove. */
    setHidden(E("detail-delete-btn"), !seg.has_override);
  }

  /* Shared by the inspector button and the Shift+Delete chord. */
  function confirmDeleteOverride(id) {
    var seg = state.segById.get(id);
    if (!seg || !seg.has_override) {
      toast("That segment has no override entry to delete.", "info");
      return;
    }
    openConfirm({
      title: "Delete the override entry?",
      message: "This removes the whole entry for " + seg.id + " from overrides.json, including its note. " +
        "The segment reverts to the pipeline classification on the next GIS re-run.",
      detail: [seg.id],
      danger: true,
      okLabel: "Delete entry"
    }).then(function (ok) { if (ok) stageDelete(seg.id); });
  }

  /* ------------------------------------------------- 11. pending changes */

  function newPending(seg) {
    return {
      id: seg.id, name: seg.name, seq: seg.seq,
      kind: "set", fields: {}, note: null,
      noteFrom: existingNote(seg), ts: Date.now()
    };
  }

  /* The ONLY writers of state.pending (§9.2). */
  function stageFields(ids, fields, note) {
    var touched = [], roads = new Set();
    ids.forEach(function (id) {
      var seg = state.segById.get(id);
      if (!seg) return;
      var pc = state.pending.get(id) || newPending(seg);
      if (pc.kind === "delete") pc.kind = "set";
      FIELD_ORDER.forEach(function (f) {
        if (!hasOwn(fields, f)) return;
        var to = fields[f];
        var from = baseValue(seg, f);
        if (sameValue(from, to)) delete pc.fields[f];
        else pc.fields[f] = { from: from, to: to };
      });
      /* Never clobber a note the user already typed with a "keep existing". */
      if (typeof note === "string" && note.trim()) pc.note = note.trim();
      else if (note === null && pc.note == null) pc.note = null;
      pc.ts = Date.now();
      if (!Object.keys(pc.fields).length && pc.note == null) state.pending.delete(id);
      else state.pending.set(id, pc);
      touched.push(id);
      roads.add(seg.road_key);
    });
    afterPendingChange(touched, roads);
    return touched;
  }

  function stageDelete(id) {
    var seg = state.segById.get(id);
    var orphan = !seg && state.orphans.some(function (o) { return o.id === id; });
    if (!seg && !orphan) return;
    var pc = seg ? (state.pending.get(id) || newPending(seg)) : {
      id: id, name: id, seq: 0, kind: "set", fields: {}, note: null, noteFrom: null, ts: Date.now()
    };
    pc.kind = "delete";
    pc.fields = {};
    pc.note = null;
    pc.ts = Date.now();
    state.pending.set(id, pc);
    afterPendingChange([id], new Set(seg ? [seg.road_key] : []));
  }

  function stageNote(ids, note) {
    var touched = [], roads = new Set();
    ids.forEach(function (id) {
      var seg = state.segById.get(id);
      if (!seg) return;
      var pc = state.pending.get(id) || newPending(seg);
      /* A staged delete removes the entry, note included, so a note recorded
         against it would be accepted here and silently dropped when the payload
         is built. Refuse it instead. */
      if (pc.kind === "delete") return;
      pc.note = typeof note === "string" && note.trim() ? note.trim() : null;
      pc.ts = Date.now();
      if (!Object.keys(pc.fields).length && pc.note == null && pc.kind !== "delete") state.pending.delete(id);
      else state.pending.set(id, pc);
      touched.push(id);
      roads.add(seg.road_key);
    });
    afterPendingChange(touched, roads);
  }

  function revert(id) {
    var seg = state.segById.get(id);
    state.pending.delete(id);
    afterPendingChange([id], new Set(seg ? [seg.road_key] : []));
  }

  /* ---- crash safety -----------------------------------------------------
     Pending edits are the only work in the app that exists nowhere else. A
     reload, a closed tab or a crash used to lose the whole sitting. They are
     mirrored into sessionStorage and restored ONLY when the file on disk is
     still the one they were staged against — a stale restore would re-apply
     decisions on top of someone else's changes. */
  function snapshotPending() {
    var out = [];
    state.pending.forEach(function (pc) { out.push(pc); });
    return out;
  }

  function persistPending() {
    try {
      if (!state.pending.size) { sessionStorage.removeItem(PENDING_KEY); return; }
      sessionStorage.setItem(PENDING_KEY, JSON.stringify({
        token: state.baseToken, ts: Date.now(), changes: snapshotPending()
      }));
    } catch (e) { /* private mode / quota — persistence is a bonus, never a gate */ }
  }

  function restorePending() {
    var raw = null;
    try { raw = sessionStorage.getItem(PENDING_KEY); } catch (e) { return; }
    if (!raw) return;
    var data = null;
    try { data = JSON.parse(raw); } catch (e) { data = null; }
    if (!data || !Array.isArray(data.changes) || !data.changes.length) return;
    if (data.token !== state.baseToken) {
      /* overrides.json moved on since these were staged: dropping them is the
         only safe answer, and saying so beats a silent disappearance. */
      try { sessionStorage.removeItem(PENDING_KEY); } catch (e) {}
      toast("Discarded " + data.changes.length + " staged " + plural(data.changes.length, "change") +
        " recovered from an earlier session — overrides.json has changed on disk since then.", "error");
      return;
    }
    var kept = 0;
    data.changes.forEach(function (pc) {
      if (!pc || !pc.id || (pc.kind !== "set" && pc.kind !== "delete")) return;
      var known = state.segById.has(pc.id) ||
        state.orphans.some(function (o) { return o.id === pc.id; });
      if (!known) return;
      if (!pc.fields || typeof pc.fields !== "object") pc.fields = {};
      state.pending.set(pc.id, pc);
      kept += 1;
    });
    if (kept) {
      toast("Restored " + kept + " staged " + plural(kept, "change") +
        " from this session — still unsaved.", "info");
    }
  }

  /* Revert-all is one click and discards everything; it needs a way back. */
  var lastRevert = null;

  function restoreSnapshot(changes) {
    var ids = [], roads = new Set();
    (changes || []).forEach(function (pc) {
      if (!pc || !pc.id) return;
      state.pending.set(pc.id, pc);
      ids.push(pc.id);
      var seg = state.segById.get(pc.id);
      if (seg) roads.add(seg.road_key);
    });
    afterPendingChange(ids, roads);
  }

  function revertAll() {
    var ids = Array.from(state.pending.keys());
    var snap = snapshotPending();
    state.pending.clear();
    var roads = new Set();
    ids.forEach(function (id) {
      var s = state.segById.get(id);
      if (s) roads.add(s.road_key);
    });
    afterPendingChange(ids, roads);
    lastRevert = snap;
    toast("Reverted " + snap.length + " staged " + plural(snap.length, "change") + ".", "info", {
      label: "Undo",
      run: function () {
        if (!lastRevert) return;
        restoreSnapshot(lastRevert);
        lastRevert = null;
        toast("Restored the reverted changes.", "info");
      }
    });
  }

  function revertLast() {
    var newest = null;
    state.pending.forEach(function (pc) { if (!newest || pc.ts >= newest.ts) newest = pc; });
    if (!newest) { toast("Nothing to undo.", "info"); return; }
    revert(newest.id);
    toast("Reverted the pending change on " + newest.id + ".", "info");
  }

  function clearAfterSave() {
    state.pending.clear();
    lastRevert = null;
    try { sessionStorage.removeItem(PENDING_KEY); } catch (e) {}
    return loadData();
  }

  function afterPendingChange(ids, roads) {
    persistPending();
    invalidateOdd();
    if (state.filters.pendingOnly) { renderAll(); }
    else {
      (ids || []).forEach(function (id) { renderRowState(id); renderMapState(id); });
      (roads || new Set()).forEach(function (k) { renderRoadRowState(k); });
    }
    renderSummary();
    renderLegend();
    renderPending();
    renderDetail();
    renderSaveControls();
  }

  function pendingFieldRows(pc) {
    var out = [];
    FIELD_ORDER.forEach(function (f) {
      if (!hasOwn(pc.fields, f)) return;
      out.push({ field: f, from: pc.fields[f].from, to: pc.fields[f].to });
    });
    return out;
  }

  function displayValue(field, v) {
    if (field === "exclude") return v === true ? "excluded" : "included";
    if (v === null || v === undefined || v === "") return "—";
    if (field === "row_ft" || field === "traveled_ft") return v + " ft";
    return String(v);
  }

  function renderPending() {
    var list = E("pending-list");
    var n = state.pending.size;
    setText(document, "#pending-count", fmtInt(n) + " pending " + plural(n, "change"));
    setHidden(E("pending-empty"), n > 0);
    /* §8.0 wants the drawer hidden at 0 pending, but #save-report, #last-save and
       #orphan-section live inside it — so it stays up while any of those has
       something to say, and carries .is-empty for the collapsed styling. */
    var panel = E("pending-panel");
    if (panel) {
      panel.hidden = !(n > 0 || state.orphans.length > 0 || state.lastSave);
      panel.classList.toggle("is-empty", n === 0);
    }
    if (!list) return;

    list.textContent = "";
    var frag = document.createDocumentFragment();
    state.pending.forEach(function (pc) {
      var li = tplNode("tpl-pending-item", ".pending-item") || tplNode("tpl-pending-item");
      if (!li) return;
      li.dataset.id = pc.id;
      setText(li, ".pending-road", pc.name + (pc.seq ? " #" + pc.seq : ""));
      setText(li, ".pending-id", pc.id);
      li.classList.toggle("is-delete", pc.kind === "delete");
      li.classList.toggle("is-exclude", hasOwn(pc.fields, "exclude") && pc.fields.exclude.to === true);

      var fieldsHost = qs(li, ".pending-fields");
      if (fieldsHost) {
        var proto = qs(fieldsHost, ".pending-field");
        if (proto) { protos.pendingField = proto.cloneNode(true); proto.remove(); }
        fieldsHost.textContent = "";
        if (pc.kind === "delete") {
          fieldsHost.appendChild(makePendingField({
            field: "delete", label: "Override", fromText: "entry", toText: "deleted"
          }));
        } else {
          pendingFieldRows(pc).forEach(function (fr) {
            fieldsHost.appendChild(makePendingField({
              field: fr.field,
              label: FIELD_LABEL[fr.field] || fr.field,
              fromText: displayValue(fr.field, fr.from),
              toText: displayValue(fr.field, fr.to)
            }));
          });
        }
      }

      var noteEl = qs(li, ".pending-note");
      var missing = qs(li, ".pending-note-missing");
      var isDelete = pc.kind === "delete";
      /* A delete discards the note — never label it "keeping". */
      var effectiveNote = isDelete ? pc.noteFrom : (pc.note != null ? pc.note : pc.noteFrom);
      if (noteEl) {
        noteEl.textContent = isDelete
          ? (pc.noteFrom ? "discards: " + pc.noteFrom : "")
          : (pc.note != null ? pc.note : (pc.noteFrom ? "(keeping) " + pc.noteFrom : ""));
        noteEl.hidden = !effectiveNote;
        noteEl.classList.toggle("is-preserved", !isDelete && pc.note == null && !!pc.noteFrom);
        noteEl.classList.toggle("is-discarded", isDelete && !!pc.noteFrom);
      }
      if (missing) missing.hidden = isDelete || !!effectiveNote;

      /* The note about to be destroyed must appear somewhere on screen before
         Save, not only in the dialog that has already closed. */
      var replacedEl = qs(li, ".pending-note-replaced");
      if (replacedEl) {
        var replaces = !isDelete && pc.note != null && pc.noteFrom && pc.note !== pc.noteFrom;
        replacedEl.textContent = replaces ? "replaces: " + pc.noteFrom : "";
        replacedEl.hidden = !replaces;
        li.classList.toggle("is-note-replaced", !!replaces);
      }

      frag.appendChild(li);
    });
    list.appendChild(frag);
  }

  function makePendingField(o) {
    var li;
    if (protos.pendingField) li = protos.pendingField.cloneNode(true);
    else {
      li = document.createElement("li");
      li.className = "pending-field";
      ["pending-field-name", "pending-from", "pending-arrow", "pending-to"].forEach(function (c) {
        var s = document.createElement("span"); s.className = c; li.appendChild(s);
      });
    }
    li.dataset.field = o.field;
    setText(li, ".pending-field-name", o.label);
    setText(li, ".pending-from", o.fromText);
    var arrow = qs(li, ".pending-arrow");
    if (arrow && !arrow.textContent.trim()) arrow.textContent = "→";
    setText(li, ".pending-to", o.toText);
    return li;
  }

  function renderOrphans() {
    var section = E("orphan-section"), list = E("orphan-list");
    if (!list) { setHidden(section, true); return; }
    list.textContent = "";
    setHidden(section, !state.orphans.length);
    if (!state.orphans.length) return;
    var frag = document.createDocumentFragment();
    state.orphans.forEach(function (o) {
      var li = tplNode("tpl-orphan-item", ".orphan-item") || tplNode("tpl-orphan-item");
      if (!li) return;
      li.dataset.id = o.id;
      setText(li, ".orphan-id", o.id);
      setText(li, ".orphan-reason", o.reason || "no matching segment");
      setText(li, ".orphan-note", (o.entry && o.entry.note) || "");
      li.title = JSON.stringify(o.entry || {});
      frag.appendChild(li);
    });
    list.appendChild(frag);
  }

  /* ----------------------------------------------- 12. selection + focus */

  function setSelection(ids, opts) {
    var prev = state.selection;
    state.selection = new Set(ids);
    var changed = new Set();
    prev.forEach(function (id) { if (!state.selection.has(id)) changed.add(id); });
    state.selection.forEach(function (id) { if (!prev.has(id)) changed.add(id); });
    changed.forEach(function (id) { renderRowState(id); });
    renderMapSelection();
    var roads = new Set();
    changed.forEach(function (id) {
      var s = state.segById.get(id);
      if (s) roads.add(s.road_key);
    });
    roads.forEach(renderRoadRowState);
    updateSelectAllState();
    renderSelectionBar();
    if (opts && opts.focus) setFocus(opts.focus, { scroll: false });
  }

  function toggleSelect(id) {
    if (state.selection.has(id)) state.selection.delete(id);
    else state.selection.add(id);
    renderRowState(id);
    renderMapSelection();
    var s = state.segById.get(id);
    if (s) renderRoadRowState(s.road_key);
    updateSelectAllState();
    renderSelectionBar();
  }

  function selectRange(toId) {
    var order = state.navIds.length ? state.navIds : state.visibleIds;
    var a = order.indexOf(state.anchorId), b = order.indexOf(toId);
    if (a === -1 || b === -1) { setSelection([toId]); state.anchorId = toId; return; }
    var lo = Math.min(a, b), hi = Math.max(a, b);
    setSelection(order.slice(lo, hi + 1));
  }

  function selectAllVisible(on) {
    if (on) setSelection(state.visibleIds.slice());
    else setSelection([]);
  }

  function updateSelectAllState() {
    var chk = E("select-all");
    if (!chk) return;
    var vis = state.visibleIds;
    var n = vis.filter(function (id) { return state.selection.has(id); }).length;
    chk.checked = vis.length > 0 && n === vis.length;
    chk.indeterminate = n > 0 && n < vis.length;
  }

  function setFocus(id, opts) {
    var prev = state.focusId;
    state.focusId = id;
    if (prev && prev !== id) renderRowState(prev);
    if (id) renderRowState(id);
    renderDetail();
    if (id && opts && opts.scroll !== false) {
      var row = state.rowById.get(id);
      if (row) {
        scrollRowIntoView(row);
        if (opts.dom !== false && row.focus) row.focus({ preventScroll: true });
      }
    }
  }

  function moveFocus(delta, extend) {
    var order = state.navIds;
    if (!order.length) return;
    var i = state.focusId ? order.indexOf(state.focusId) : -1;
    var next = i === -1 ? (delta > 0 ? 0 : order.length - 1) : Math.min(order.length - 1, Math.max(0, i + delta));
    var id = order[next];
    if (!id) return;
    setFocus(id);
    if (extend) {
      if (!state.anchorId) state.anchorId = id;
      selectRange(id);
    } else {
      setSelection([id]);
      state.anchorId = id;
    }
  }

  function renderSelectionBar() {
    var sel = Array.from(state.selection);
    var roads = new Set(), ft = 0;
    sel.forEach(function (id) {
      var s = state.segById.get(id);
      if (!s) return;
      roads.add(s.road_key);
      ft += segLength(s);
    });
    var hiddenIds = sel.filter(function (id) { return !state.visibleSet.has(id); });
    var hidden = hiddenIds.length;
    var text = sel.length
      ? fmtInt(sel.length) + " " + plural(sel.length, "segment") + " selected · " +
        fmtInt(roads.size) + " " + plural(roads.size, "road") + " · " + fmtFt(ft)
      : "Nothing selected";
    setText(document, "#selection-count", text);

    /* A selection survives a filter change on purpose — losing it mid-task is
       worse than carrying it. But then a bulk action can reach segments that
       are not on screen, so the count is a warning you can act on, not a
       parenthetical. */
    var warnBtn = E("selection-hidden-warn");
    if (warnBtn) {
      warnBtn.hidden = hidden === 0;
      warnBtn.textContent = hidden
        ? fmtInt(hidden) + " hidden by filters — limit to visible"
        : "";
    }
    var bar0 = E("bulk-bar");
    if (bar0) bar0.classList.toggle("has-hidden-selection", hidden > 0);

    var empty = sel.length === 0;
    qsa(E("type-palette"), "button.type-btn").forEach(function (b) { b.disabled = empty; });
    ["bulk-ownership", "bulk-ownership-apply", "bulk-use", "bulk-use-apply", "bulk-exclude", "bulk-clear-note", "selection-clear", "selection-invert"]
      .forEach(function (id) { var n = E(id); if (n) n.disabled = empty; });
    var bar = E("bulk-bar");
    if (bar) bar.classList.toggle("has-selection", !empty);
  }

  /* ------------------------------------------------------ 13. note text */

  /* §12 — ASCII "->", one sentence, ends with a period. */
  function oldList(values) {
    var vals = uniq(values.map(function (v) { return v || ""; }));
    var codes = vals.filter(Boolean);
    if (!codes.length) return "—";
    if (codes.every(function (c) { return state.typeByCode.has(c); })) codes = sortTypeCodes(codes);
    else codes.sort();
    return codes.join("/");
  }

  function wholeRoadKey(ids) {
    if (!ids.length) return null;
    var seg0 = state.segById.get(ids[0]);
    if (!seg0) return null;
    var key = seg0.road_key;
    var all = ids.every(function (id) {
      var s = state.segById.get(id);
      return s && s.road_key === key;
    });
    if (!all) return null;
    var road = state.roadByKey.get(key);
    if (!road) return null;
    var set = new Set(ids);
    return road.segment_ids.every(function (id) { return set.has(id); }) ? key : null;
  }

  function generateNote(action) {
    var ids = action.ids || [];
    var segs = ids.map(function (id) { return state.segById.get(id); }).filter(Boolean);
    var parts = [];

    FIELD_ORDER.forEach(function (field) {
      if (!hasOwn(action.fields, field)) return;
      var to = action.fields[field];
      var froms = segs.map(function (s) { return baseValue(s, field); });

      if (field === "type") {
        if (to === null) {
          parts.push("Type override removed; reverts to the pipeline classification on the next re-run.");
          return;
        }
        /* action.roadKey is the road the USER aimed at; ids are only the
           segments that actually change, so {OLDLIST} never lists {NEW}. */
        var rk = action.roadKey || wholeRoadKey(ids);
        var rkN = rk && state.roadByKey.has(rk) ? state.roadByKey.get(rk).segment_ids.length : 0;
        if (segs.length === 1 && rkN < 2) {   /* 130 roads are a single segment */
          var from1 = froms[0];
          parts.push(from1 ? "Board correction: " + from1 + " -> " + to + "."
                           : "Board classification: " + to + ".");
        } else if (rk && state.roadByKey.has(rk)) {
          var road = state.roadByKey.get(rk);
          parts.push(road.name + ": " + to + " for its full length (" + road.segment_ids.length +
            " " + plural(road.segment_ids.length, "segment") + "); corrects " + oldList(froms) + ".");
        } else if (uniq(segs.map(function (s) { return s.road_key; })).length === 1) {
          parts.push(segs[0].name + " (" + segs.length + " " + plural(segs.length, "segment") + "): " +
            to + ", corrects " + oldList(froms) + ".");
        } else {
          parts.push("Board correction: " + to + " applied to " + segs.length + " " +
            plural(segs.length, "segment") + " (was " + oldList(froms) + ").");
        }
      } else if (field === "present_use") {
        if (to === null) {
          parts.push("Present-use record removed.");
        } else if (to === "Driveway") {
          parts.push("Recorded as functioning today as a Driveway (Art 3 \u00a75.C.3.g); "
                   + "the Type shown remains the Type that would apply on conversion "
                   + "under \u00a77.F.");
        } else {
          parts.push("Present use recorded as " + to + " (Art 3 \u00a75.C.3.g).");
        }
      } else if (field === "ownership") {
        if (to === null) {
          parts.push("Ownership Category override removed.");
        } else {
          var ol = oldList(froms);
          parts.push("Ownership Category recorded as " + to + (ol === "—" ? "" : ", was " + ol) + ".");
        }
      } else if (field === "exclude") {
        parts.push(to === true
          ? "Not a thoroughfare: excluded from the Inventory."
          : "Exclusion removed; the segment is a thoroughfare after all.");
      } else if (field === "row_ft") {
        parts.push(to === null ? "Right-of-way width override removed."
                               : "Right-of-way width recorded as " + to + " ft.");
      } else if (field === "traveled_ft") {
        parts.push(to === null ? "Traveled way width override removed."
                               : "Traveled way width recorded as " + to + " ft.");
      } else if (field === "nonconformity") {
        parts.push(to === null ? "Nonconformity note removed."
                               : "Nonconformity recorded: " + String(to).replace(/\.$/, "") + ".");
      }
    });

    return parts.join(" ");
  }

  /* --------------------------------------------------------- 14. dialogs */

  function openDialog(dlg) {
    if (!dlg) return;
    if (typeof dlg.showModal === "function" && !dlg.open) { try { dlg.showModal(); return; } catch (e) { /* fall through */ } }
    dlg.setAttribute("open", "");
    dlg.hidden = false;
  }
  function closeDialog(dlg) {
    if (!dlg) return;
    if (typeof dlg.close === "function" && dlg.open) { try { dlg.close(); return; } catch (e) { /* fall through */ } }
    dlg.removeAttribute("open");
    dlg.hidden = true;
  }
  function anyDialogOpen() {
    return !!document.querySelector("dialog[open]");
  }

  var noteResolve = null;
  var confirmResolve = null;

  /* Resolves {note: string} · {note: null} (keep existing) · null (cancelled). */
  function openNoteDialog(opts) {
    var dlg = E("note-dialog");
    var generated = opts.generated || "";
    var targets = opts.targets || [];
    /* Targets that already carry a hand-written note in overrides.json. These
       notes are the written record of a Planning Board decision; the file has
       no other copy of them. */
    var withNotes = targets.filter(function (id) {
      var s = state.segById.get(id);
      return !!existingNote(s);
    });
    /* Also count notes only staged so far — replacing one of those loses
       wording the user typed in this sitting, which is just as surprising. */
    var stagedNotes = targets.filter(function (id) {
      var pc = state.pending.get(id);
      return !!(pc && pc.note) && withNotes.indexOf(id) === -1;
    });
    var atRisk = withNotes.length + stagedNotes.length;

    if (!dlg) return Promise.resolve({ note: generated || null });
    /* "Use the suggested note without asking" is a convenience for entries that
       have no note to lose. It is NOT consent to overwrite existing wording, so
       the moment anything is at risk the dialog opens anyway — otherwise a
       preference ticked once on road 3 silently rewrites the notes on roads
       4..20 with a generated one-liner and nothing on screen ever says so. */
    if (state.autoNote && !opts.force && atRisk === 0) {
      return Promise.resolve({ note: generated || null });
    }

    setText(document, "#note-dialog-title",
      targets.length === 1 ? "Note for this change" : "Note for " + targets.length + " changes");
    setText(document, "#note-dialog-summary", opts.summary || "");

    var tl = E("note-dialog-targets");
    if (tl) {
      tl.textContent = "";
      targets.slice(0, 20).forEach(function (id) {
        var li = document.createElement("li");
        li.textContent = id;
        tl.appendChild(li);
      });
      if (targets.length > 20) {
        var more = document.createElement("li");
        more.className = "is-more";
        more.textContent = "+" + (targets.length - 20) + " more";
        tl.appendChild(more);
      }
    }

    var ex = E("note-existing");
    if (ex) {
      /* CONTRACT §8.7 hides this whenever the count is not exactly 1. That is
         wrong in the one case that matters most: a whole-road action over
         segments where several already carry a hand-written note. The dialog
         would then say nothing while the confirm button replaces all of them.
         Superset: 1 note → quote it (as specified); >1 → say how many are at
         stake and point at "Keep existing note". */
      var exLabel = ex.previousElementSibling;
      ex.classList.toggle("is-multi", atRisk > 1);
      if (atRisk === 1 && withNotes.length === 1) {
        ex.hidden = false;
        if (exLabel) exLabel.textContent = "Existing note (will be replaced):";
        ex.textContent = existingNote(state.segById.get(withNotes[0])) || "";
      } else if (atRisk === 1 && stagedNotes.length === 1) {
        ex.hidden = false;
        if (exLabel) exLabel.textContent = "Note staged for this segment (will be replaced):";
        ex.textContent = (state.pending.get(stagedNotes[0]) || {}).note || "";
      } else if (atRisk > 1) {
        ex.hidden = false;
        if (exLabel) exLabel.textContent = "Existing notes";
        ex.textContent = atRisk + " of these " + targets.length +
          " segments already carry a note" +
          (withNotes.length && stagedNotes.length
            ? " (" + withNotes.length + " on disk, " + stagedNotes.length + " staged here)"
            : withNotes.length ? " in overrides.json" : " staged here") +
          ". Replacing rewrites all " + atRisk + "; “Keep existing note” stages the change " +
          "and leaves every one of them untouched.";
      } else {
        ex.hidden = true;
        if (exLabel) exLabel.textContent = "Existing note (will be replaced):";
        ex.textContent = "";
      }
    }

    var input = E("note-input");
    if (input) {
      input.value = opts.initial !== undefined ? opts.initial : generated;
      input.dataset.generated = generated;
    }

    /* When existing wording is at stake, keeping it is the safe answer, so it
       becomes the primary button and takes the focus. The replacing action
       stays one keystroke away — it is just no longer what Enter does. */
    var keep = E("note-keep-btn");
    var confirmBtn = E("note-confirm");
    var atRiskNow = atRisk > 0 && !opts.replacing;
    if (keep) {
      keep.disabled = atRisk === 0;
      keep.classList.toggle("btn-primary", atRiskNow);
      keep.classList.toggle("btn-quiet", !atRiskNow);
      keep.classList.toggle("btn-sm", !atRiskNow);
    }
    if (confirmBtn) {
      confirmBtn.classList.toggle("btn-primary", !atRiskNow);
      confirmBtn.classList.toggle("btn-quiet", atRiskNow);
      confirmBtn.textContent = atRiskNow ? "Replace the note" : "Stage change";
    }

    var pref = E("pref-auto-note");
    if (pref) pref.checked = state.autoNote;
    /* Say plainly why the dialog appeared despite the preference. */
    var prefHost = pref ? pref.closest("label") : null;
    var prefNote = E("pref-auto-note-override");
    if (prefHost && !prefNote) {
      prefNote = document.createElement("span");
      prefNote.id = "pref-auto-note-override";
      prefNote.className = "dialog-hint is-warn";
      prefHost.parentNode.insertBefore(prefNote, prefHost.nextSibling);
    }
    if (prefNote) {
      prefNote.textContent = (state.autoNote && atRisk > 0)
        ? "Asked anyway: " + atRisk + " of these " + targets.length + " " +
          plural(targets.length, "segment") + " already " +
          plural(atRisk, "carries", "carry") + " a note. The suggestion is never " +
          "applied silently over existing wording."
        : "";
      prefNote.hidden = !prefNote.textContent;
    }

    openDialog(dlg);
    if (atRiskNow && keep && !keep.disabled) keep.focus();
    else if (input) { input.focus(); input.select(); }

    return new Promise(function (resolve) {
      noteResolve = resolve;
    });
  }

  function settleNote(value) {
    var r = noteResolve;
    noteResolve = null;
    closeDialog(E("note-dialog"));
    if (r) r(value);
  }

  function openConfirm(opts) {
    var dlg = E("confirm-dialog");
    if (!dlg) return Promise.resolve(window.confirm(opts.message || "Are you sure?"));
    setText(document, "#confirm-title", opts.title || "Confirm");
    setText(document, "#confirm-message", opts.message || "");
    var det = E("confirm-detail");
    if (det) {
      det.textContent = "";
      var items = opts.detail || [];
      items.slice(0, 20).forEach(function (d) {
        var li = document.createElement("li");
        li.textContent = d;
        det.appendChild(li);
      });
      if (items.length > 20) {
        var more = document.createElement("li");
        more.textContent = "+" + (items.length - 20) + " more";
        det.appendChild(more);
      }
      det.hidden = items.length === 0;
    }
    var ok = E("confirm-ok");
    if (ok) {
      ok.classList.toggle("is-danger", !!opts.danger);
      if (opts.okLabel) ok.textContent = opts.okLabel;
    }
    openDialog(dlg);
    if (ok && ok.focus) ok.focus();
    return new Promise(function (resolve) { confirmResolve = resolve; });
  }

  function settleConfirm(value) {
    var r = confirmResolve;
    confirmResolve = null;
    closeDialog(E("confirm-dialog"));
    if (r) r(value);
  }

  /* ---------------------------------------------------------- 15. toasts */

  function toast(message, level, action) {
    var host = E("toast-container");
    if (!host) { if (level === "error") console.error(message); else console.log(message); return; }
    var node = tplNode("tpl-toast", ".toast") || tplNode("tpl-toast");
    if (!node) {
      node = document.createElement("div");
      node.className = "toast";
      var m = document.createElement("span"); m.className = "toast-message"; node.appendChild(m);
      var c = document.createElement("button"); c.className = "toast-close"; c.type = "button"; c.textContent = "×"; node.appendChild(c);
    }
    node.dataset.level = level || "info";
    if (!setText(node, ".toast-message", message)) node.textContent = message;

    /* An optional inline action, used for Undo: a destructive-but-cheap step
       like "Revert all" needs a way back that does not depend on remembering
       what was staged. */
    if (action && action.label && typeof action.run === "function") {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "toast-action";
      btn.textContent = action.label;
      btn.addEventListener("click", function () {
        node.remove();
        action.run();
      });
      var closeBtn = qs(node, ".toast-close");
      if (closeBtn) node.insertBefore(btn, closeBtn);
      else node.appendChild(btn);
    }

    host.appendChild(node);
    if (level !== "error") {
      setTimeout(function () { if (node.parentNode) node.remove(); }, action ? 14000 : 6000);
    }
  }

  /* ------------------------------------------------- 16. staging actions */

  /* Would this change alter what is CURRENTLY staged-or-on-disk for the segment?
     Measured against currentValue, never baseValue: a segment sitting at S4 on
     disk with R2 staged must still accept "set to S4" — that is how you take an
     edit back. */
  function wouldChange(seg, fields) {
    var pc = state.pending.get(seg.id);
    if (pc && pc.kind === "delete") return true;   // a delete is pending; any value differs
    for (var i = 0; i < FIELD_ORDER.length; i++) {
      var f = FIELD_ORDER[i];
      if (!hasOwn(fields, f)) continue;
      if (!sameValue(currentValue(seg, f), fields[f])) return true;
    }
    return false;
  }

  /* Does this action put every named field back to exactly its on-disk value?
     Then it is an un-stage, not a new decision: no note is warranted and none
     is asked for. */
  function fieldsMatchBase(seg, fields) {
    for (var i = 0; i < FIELD_ORDER.length; i++) {
      var f = FIELD_ORDER[i];
      if (!hasOwn(fields, f)) continue;
      if (!sameValue(baseValue(seg, f), fields[f])) return false;
    }
    return true;
  }

  /* Drops the named fields from a pending entry (and the entry itself once its
     last field goes). A note that was staged alongside those fields goes with
     them; a note staged on its own through "Note…" is left alone. */
  function unstageFields(ids, fields) {
    var touched = [], roads = new Set();
    ids.forEach(function (id) {
      var pc = state.pending.get(id);
      var seg = state.segById.get(id);
      if (!pc || !seg) return;
      if (pc.kind === "delete") {
        state.pending.delete(id);
      } else {
        var hadFields = Object.keys(pc.fields).length > 0;
        FIELD_ORDER.forEach(function (f) { if (hasOwn(fields, f)) delete pc.fields[f]; });
        if (!Object.keys(pc.fields).length && (hadFields || pc.note == null)) state.pending.delete(id);
        else { pc.ts = Date.now(); state.pending.set(id, pc); }
      }
      touched.push(id);
      roads.add(seg.road_key);
    });
    afterPendingChange(touched, roads);
    return touched;
  }

  /* Every value change funnels through here so a note is always offered.
     Segments that already hold the requested value are dropped BEFORE the note
     dialog — otherwise "all of Main Street is S1" on a road that is already S1
     would stage a dozen no-op entries and overwrite a dozen hand-written notes. */
  function stageWithNote(ids, fields, opts) {
    opts = opts || {};
    var targets = ids.filter(function (id) { return state.segById.has(id); });
    if (!targets.length) {
      toast("Select segments first — click a row, a road checkbox, or a line on the map.", "info");
      return Promise.resolve(false);
    }
    var changed = targets.filter(function (id) { return wouldChange(state.segById.get(id), fields); });

    /* Of the segments that change, the ones landing back on their on-disk value
       are un-staging an earlier edit. Those are applied straight away and never
       reach the note dialog — "put Deer Meadow Road back to R2" is a retraction,
       not a Board decision that wants a written justification. */
    var reverting = changed.filter(function (id) {
      return state.pending.has(id) && fieldsMatchBase(state.segById.get(id), fields);
    });
    var editing = changed.filter(function (id) { return reverting.indexOf(id) === -1; });
    if (reverting.length) unstageFields(reverting, fields);

    if (!editing.length) {
      if (reverting.length) {
        toast("Cleared the staged change on " + reverting.length + " " +
          plural(reverting.length, "segment") + " — back to the value on disk.", "info");
        return Promise.resolve(true);
      }
      toast(targets.length === 1
        ? "That segment already holds this value — nothing staged."
        : "All " + targets.length + " selected segments already hold this value — nothing staged.", "info");
      return Promise.resolve(false);
    }
    var action = { ids: editing, fields: fields, roadKey: wholeRoadKey(targets) };
    var generated = generateNote(action);
    /* The caller's summary describes the intent ("Main Street → S1 (12
       segments)"), but the dialog's title and target chips count only the
       segments that actually change. Reconcile the two so the dialog does not
       say 12 in one line and 3 in the next. */
    var summary = opts.summary || generated;
    var skippedNow = targets.length - changed.length;
    if (skippedNow) {
      summary += " · " + skippedNow + " already " +
        (skippedNow === 1 ? "holds that value and is" : "hold that value and are") + " left alone";
    }
    if (reverting.length) {
      summary += " · " + reverting.length + " staged " + plural(reverting.length, "edit") +
        " cleared back to the value on disk";
    }
    return openNoteDialog({
      targets: editing,
      generated: generated,
      summary: summary,
      force: opts.force
    }).then(function (res) {
      if (!res) return reverting.length > 0;        // cancelled: nothing further staged
      stageFields(editing, fields, res.note);
      setFocus(editing[0], { scroll: false, dom: false });
      if (opts.toast !== false) {
        toast("Staged " + editing.length + " " + plural(editing.length, "change") +
          (skippedNow ? " (" + skippedNow + " already matched)" : "") +
          (reverting.length ? " (" + reverting.length + " cleared)" : "") +
          " — nothing is written until you press Save.", "info");
      }
      return true;
    });
  }

  function applyTypeToIds(ids, code) {
    return stageWithNote(ids, { type: code || null }, {
      summary: summariseTypeAction(ids, code)
    });
  }

  function summariseTypeAction(ids, code) {
    var rk = wholeRoadKey(ids);
    if (rk) {
      var road = state.roadByKey.get(rk);
      var n = road.segment_ids.length;
      /* The road row's own label reads "6 of 9 segments" under a filter, so an
         action that covers all nine has to say so here or the two disagree. */
      var hidden = road.segment_ids.filter(function (i) { return !state.visibleSet.has(i); }).length;
      return road.name + " → " + (code || "—") + " (all " + n + " " + plural(n, "segment") +
        (hidden ? ", " + hidden + " hidden by the current filter" : "") + ")";
    }
    if (ids.length === 1) {
      var s = state.segById.get(ids[0]);
      return s ? s.name + " #" + s.seq + " → " + (code || "—") : ids[0];
    }
    return ids.length + " " + plural(ids.length, "segment") + " → " + (code || "—");
  }

  function applyTypeToSelection(code) {
    if (!state.selection.size) {
      toast("Select segments first — click a row, a road checkbox, or a line on the map.", "info");
      return;
    }
    applyTypeToIds(Array.from(state.selection), code);
  }

  function applyPresentUseToIds(ids, value) {
    return stageWithNote(ids, { present_use: value }, {
      summary: ids.length + " " + plural(ids.length, "segment") + " → present use "
             + (value || "not recorded")
    });
  }

  function applyOwnershipToIds(ids, value) {
    return stageWithNote(ids, { ownership: value }, {
      summary: ids.length + " " + plural(ids.length, "segment") + " → ownership " + (value || "not recorded")
    });
  }

  function toggleExcludeIds(ids) {
    ids = ids.filter(function (id) { return state.segById.has(id); });
    if (!ids.length) {
      toast("Select segments first — click a row, a road checkbox, or a line on the map.", "info");
      return Promise.resolve(false);
    }
    var allExcluded = ids.every(function (id) { return effExcluded(state.segById.get(id)); });
    var to = !allExcluded;
    var applying = E("apply-inventory") ? E("apply-inventory").checked : true;
    var msg = to
      ? "Mark " + ids.length + " " + plural(ids.length, "segment") + " as not a thoroughfare?"
      : "Remove the exclusion from " + ids.length + " " + plural(ids.length, "segment") + "?";
    var detailMsg = to && applying
      ? " This removes the segment from the rendered inventory. Restoring it requires a GIS pipeline re-run or the backup file."
      : (to ? " The exclusion is recorded in overrides.json; the rendered inventory is left alone." : "");

    /* Two things a selection can be carrying that you would not choose on
       purpose: segments the filters hide, and the note-only OPEN ITEM markers
       that are waiting on Ben's check of the Town's road records. Name them in
       the dialog rather than burying them in a list of ids. */
    var hidden = ids.filter(function (id) { return !state.visibleSet.has(id); });
    var openItems = ids.filter(function (id) { return isNoteOnly(state.segById.get(id)); });
    if (hidden.length) {
      detailMsg += " " + hidden.length + " of them " +
        plural(hidden.length, "is", "are") + " not visible under the current filters.";
    }
    if (openItems.length) {
      detailMsg += " " + openItems.length + " " +
        plural(openItems.length, "is an OPEN ITEM", "are OPEN ITEMS") +
        " (note-only, awaiting the Town's road records): " + openItems.join(", ") + ".";
    }

    return openConfirm({
      title: to ? "Exclude from the Inventory" : "Un-exclude",
      message: msg + detailMsg,
      detail: ids,
      danger: to,
      okLabel: to ? "Exclude" : "Un-exclude"
    }).then(function (ok) {
      if (!ok) return false;
      return stageWithNote(ids, { exclude: to }, {
        summary: (to ? "Exclude " : "Un-exclude ") + ids.length + " " + plural(ids.length, "segment")
      });
    });
  }

  function editNoteForIds(ids) {
    ids = ids.filter(function (id) { return state.segById.has(id); });
    if (!ids.length) { toast("Select or focus a segment first.", "info"); return; }
    var deleting = ids.filter(function (id) {
      var pc = state.pending.get(id);
      return !!(pc && pc.kind === "delete");
    });
    if (deleting.length) {
      ids = ids.filter(function (id) { return deleting.indexOf(id) === -1; });
      toast(deleting.length + " " + plural(deleting.length, "segment") +
        " " + plural(deleting.length, "has", "have") + " a staged entry deletion, which discards the note — " +
        "revert the deletion first to write one.", "error");
      if (!ids.length) return;
    }
    var existing = null;
    for (var i = 0; i < ids.length; i++) {
      var n = existingNote(state.segById.get(ids[i]));
      if (n) { existing = n; break; }
    }
    var pc = state.pending.get(ids[0]);
    var initial = pc && pc.note ? pc.note : (existing || "");
    var generated = pc ? generateNote({ ids: ids, fields: pendingFieldsToObject(pc) }) : "";
    openNoteDialog({
      targets: ids,
      generated: generated || initial,
      initial: initial,
      summary: ids.length === 1 ? ids[0] : ids.length + " " + plural(ids.length, "segment"),
      force: true,
      replacing: true        /* the user came here to write a note; that is the point */
    }).then(function (res) {
      if (!res) return;
      stageNote(ids, res.note);
    });
  }

  function pendingFieldsToObject(pc) {
    var out = {};
    FIELD_ORDER.forEach(function (f) { if (hasOwn(pc.fields, f)) out[f] = pc.fields[f].to; });
    return out;
  }

  /* ------------------------------------------------------- 17. save flow */

  function buildPayload() {
    var changes = [], ids = [];
    state.pending.forEach(function (pc) {
      var ch = toChange(pc);
      if (!ch) return;
      changes.push(ch);
      ids.push(pc.id);
    });
    state.lastPayloadIds = ids;
    return {
      contract: CONTRACT_VERSION,
      base_token: state.baseToken,
      apply_to_inventory: E("apply-inventory") ? !!E("apply-inventory").checked : true,
      changes: changes
    };
  }

  function toChange(pc) {
    if (pc.kind === "delete") return { id: pc.id, delete: true };
    var set = {};
    FIELD_ORDER.forEach(function (f) {
      if (!hasOwn(pc.fields, f)) return;
      var to = pc.fields[f].to;
      if (f === "exclude") set.exclude = to === true;   // false → server removes the key
      else set[f] = to;                                  // null → server removes the key
    });
    if (typeof pc.note === "string" && pc.note.trim()) set.note = pc.note.trim();
    if (!Object.keys(set).length) return null;           // never send an empty `set`
    return { id: pc.id, set: set };
  }

  function setSaveStatus(stateName, text) {
    var el = E("save-status");
    if (!el) return;
    el.dataset.state = stateName;
    el.textContent = text || "";
  }

  function setConn(kind, text) {
    var el = E("conn-status");
    if (!el) return;
    el.classList.toggle("is-ok", kind === "ok");
    el.classList.toggle("is-error", kind === "error");
    el.classList.toggle("is-saving", kind === "saving");
    el.textContent = text || kind;
  }

  function renderSaveControls() {
    var n = state.pending.size;
    var btn = E("save-btn");
    if (btn) btn.disabled = n === 0 || state.saving || !!state.contractMismatch;
    var vb = E("validate-btn");
    if (vb) vb.disabled = n === 0 || state.saving;
    var clear = E("pending-clear");
    if (clear) clear.disabled = n === 0;
  }

  function clearValidationMarks() {
    qsa(E("pending-list"), "li.pending-item").forEach(function (li) {
      li.classList.remove("is-invalid");
      var e = qs(li, ".pending-error");
      if (e) e.remove();
    });
  }

  function showValidationErrors(details) {
    clearValidationMarks();
    (details || []).forEach(function (d) {
      var id = d.id || state.lastPayloadIds[d.index];
      if (!id) return;
      var li = qs(E("pending-list"), 'li.pending-item[data-id="' + cssEscape(id) + '"]');
      if (!li) return;
      li.classList.add("is-invalid");
      var p = qs(li, ".pending-error");
      if (!p) {
        p = document.createElement("p");
        p.className = "pending-error";
        li.appendChild(p);
      }
      p.textContent = (d.field ? d.field + ": " : "") + (d.message || d.code || "invalid");
    });
  }

  function cssEscape(s) {
    if (window.CSS && CSS.escape) return CSS.escape(s);
    return String(s).replace(/["\\]/g, "\\$&");
  }

  function doValidate() {
    if (!state.pending.size) return;
    setSaveStatus("validating", "Checking…");
    clearValidationMarks();
    api("/api/validate", { method: "POST", body: buildPayload() }).then(function (res) {
      var w = res.would_write || {};
      var bits = ["Valid — would write " + (w.overrides || 0) + " override " + plural(w.overrides || 0, "entry", "entries")];
      if (w.inventory != null) bits.push(w.inventory + " inventory " + plural(w.inventory, "segment"));
      if ((res.notes_missing || []).length) bits.push((res.notes_missing.length) + " without a note");
      if ((res.removals || []).length) bits.push((res.removals.length) + " removal(s)");
      setSaveStatus("ok", bits.join(" · ") + ".");
      (res.warnings || []).forEach(function (x) { toast(x.message, "warn"); });
    }).catch(function (err) { handleSaveError(err, "validate"); });
  }

  function doSave() {
    if (!state.pending.size || state.saving) return;
    if (state.contractMismatch) { toast("Contract version mismatch — saving is disabled.", "error"); return; }
    state.saving = true;
    renderSaveControls();
    setConn("saving", "saving…");
    setSaveStatus("saving", "Writing…");
    clearValidationMarks();
    var payload = buildPayload();
    api("/api/save", { method: "POST", body: payload }).then(function (res) {
      state.saving = false;
      state.lastSave = res;
      renderSaveReport(res);
      var invFailed = res.inventory && res.inventory.written === false && res.inventory.error;
      if (invFailed) {
        setSaveStatus("warn", "overrides.json saved — the inventory write failed: " +
          (res.inventory.error.message || res.inventory.error.code));
        toast("Saved the durable record, but the rendered inventory was not updated. Re-run the GIS export or try again.", "warn");
      } else {
        setSaveStatus("ok", "Saved.");
        toast("Saved " + payload.changes.length + " " + plural(payload.changes.length, "change") + ".", "info");
      }
      (res.warnings || []).forEach(function (w) { toast(w.message, "warn"); });
      setConn("ok", "connected");
      return clearAfterSave().catch(function () { /* already toasted by loadData */ });
    }).catch(function (err) {
      state.saving = false;
      handleSaveError(err, "save");
    }).then(function () {
      state.saving = false;
      renderSaveControls();
    });
  }

  function handleSaveError(err, phase) {
    renderSaveControls();
    /* doSave() sets the badge to "saving…" and only its success path clears it,
       so every failure below used to leave the header claiming a write was
       still in flight. If the server answered at all it is reachable; the
       offline branch re-sets this a few lines down. */
    if (err.status !== undefined) setConn("ok", "connected");
    if (err.status === 409) {
      var n = state.pending.size;
      setSaveStatus("error", "overrides.json changed on disk — reload to merge.");
      showBlocking("overrides.json changed on disk since this page loaded, so nothing was written. " +
        "Your " + n + " pending " + plural(n, "change") + " " + (n === 1 ? "is" : "are") +
        " still here. Dismiss this to keep working, or use Reload (which discards them) to pick up the new file.");
      toast("Save refused: the file on disk is newer than this page.", "error");
      return;
    }
    if (err.code === "validation_failed") {
      setSaveStatus("error", err.message || "Validation failed; nothing was written.");
      showValidationErrors(err.details);
      toast(err.message || "Validation failed — nothing was written.", "error");
      return;
    }
    if (err.status === undefined) {
      setConn("error", "offline");
      setSaveStatus("error", "Could not reach the local server. Nothing was written; your changes are still here.");
      toast("Network error during " + phase + " — the pending list is untouched.", "error");
      return;
    }
    setSaveStatus("error", (err.code || "error") + ": " + err.message);
    toast((err.code || "error") + ": " + err.message, "error");
  }

  function renderSaveReport(res) {
    var host = E("save-report");
    if (host) {
      host.textContent = "";
      var ov = res.overrides || {};
      var inv = res.inventory || {};
      var lines = [];
      if (ov.written) {
        lines.push("overrides.json — " + (ov.entries_before || 0) + " → " + (ov.entries_after || 0) + " entries" +
          (ov.created && ov.created.length ? ", " + ov.created.length + " created" : "") +
          (ov.updated && ov.updated.length ? ", " + ov.updated.length + " updated" : "") +
          (ov.removed && ov.removed.length ? ", " + ov.removed.length + " removed" : ""));
        /* Notes are the written record of a Board decision and have no second
           copy outside the backup, so a replacement is reported as its own line
           rather than folded into "N updated". */
        var nr = ov.notes_replaced || [];
        if (nr.length) {
          lines.push(nr.length + " existing " + plural(nr.length, "note") + " replaced (" +
            nr.slice(0, 6).map(function (r) { return r.id; }).join(", ") +
            (nr.length > 6 ? ", …" : "") + ") — the previous wording is in the backup");
        }
        if (ov.backup) lines.push("backup: " + basename(ov.backup));
        if (ov.backups_pruned && ov.backups_pruned.length) lines.push("pruned " + ov.backups_pruned.length + " old backup(s)");
      } else {
        lines.push("overrides.json — not written (" + (ov.reason || "no changes") + ")");
      }
      if (inv.written) {
        lines.push("inventory.json — " + (inv.segments_before || 0) + " → " + (inv.segments_after || 0) +
          " segments, " + (inv.fields_updated || 0) + " field(s) updated");
        if (inv.backup) lines.push("backup: " + basename(inv.backup));
        if (inv.segments_removed && inv.segments_removed.length) lines.push("removed from the inventory: " + inv.segments_removed.join(", "));
        (inv.skipped || []).forEach(function (s) {
          lines.push("skipped " + s.id + " · " + (s.field || "") + " (" + s.reason + ")");
        });
      } else if (inv.error) {
        lines.push("inventory.json — FAILED: " + (inv.error.message || inv.error.code));
      } else {
        lines.push("inventory.json — not written (" + (inv.reason || "not requested") + ")");
      }
      lines.forEach(function (t) {
        var p = document.createElement("p");
        p.className = "save-report-line";
        p.textContent = t;
        host.appendChild(p);
      });
    }
    var last = E("last-save");
    if (last) {
      var bk = res.overrides && res.overrides.backup ? " — backup " + basename(res.overrides.backup) : "";
      last.textContent = "Last saved " + fmtTime(res.saved_at) + bk;
    }
  }

  function showBlocking(message) {
    var overlay = E("blocking-overlay");
    if (!overlay) { window.alert(message); return; }
    setText(document, "#blocking-message", message);
    overlay.hidden = false;
    var dismiss = E("blocking-dismiss");
    if (dismiss) dismiss.focus();
  }
  function hideBlocking() { setHidden(E("blocking-overlay"), true); }

  /* --------------------------------------------------- 18. filter wiring */

  function buildFilterControls() {
    fillOptions(E("filter-type"),
      [{ value: "", label: "All Types" }]
        .concat(state.types.map(function (t) { return { value: t.code, label: t.code + " — " + t.name }; }))
        .concat([{ value: "__none__", label: "Untyped" }]),
      { value: state.filters.type });

    fillOptions(E("filter-family"),
      [{ value: "", label: "All families" },
       { value: "S", label: "Street (urban)" },
       { value: "R", label: "Road (rural)" }],
      { value: state.filters.family });

    fillOptions(E("filter-district"),
      [{ value: "", label: "All Districts" }]
        .concat(state.districts.map(function (d) { return { value: d, label: d }; })),
      { value: state.filters.district });

    fillOptions(E("filter-ownership"),
      [{ value: "", label: "All Ownership" }]
        .concat(state.ownershipCategories.map(function (o) { return { value: o, label: o }; }))
        .concat([{ value: "__blank__", label: "Not recorded" }]),
      { value: state.filters.ownership });

    fillOptions(E("filter-use"),
      [{ value: "", label: "All present use" }]
        .concat(state.presentUseValues.map(function (v) {
          return { value: v, label: v === "Driveway" ? "Driveway (D)" : v };
        }))
        .concat([{ value: "__blank__", label: "Not reviewed" }]),
      { value: state.filters.use });

    fillOptions(E("filter-override"),
      [{ value: "", label: "Any" },
       { value: "has", label: "Has override" },
       { value: "none", label: "No override" },
       { value: "typed", label: "Type overridden" },
       { value: "noteonly", label: "Note-only" },
       { value: "excluded", label: "Excluded" },
       { value: "drift", label: "Drift vs inventory" },
       { value: "odd", label: "Differs from its road" }],
      { value: state.filters.override });

    fillOptions(E("bulk-ownership"),
      ownershipOptionList("Set ownership…", "Clear (not recorded)"), { value: "" });

    fillOptions(E("bulk-use"),
      presentUseOptionList("Set present use…", "Clear (not reviewed)"), { value: "" });

    var search = E("filter-search");
    if (search && search.value !== state.filters.search) search.value = state.filters.search;
    var pend = E("filter-pending");
    if (pend) pend.checked = state.filters.pendingOnly;
  }

  function buildTypePalette() {
    var host = E("type-palette");
    if (!host) return;
    host.textContent = "";
    var frag = document.createDocumentFragment();
    state.types.forEach(function (t, i) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "type-btn";
      b.dataset.type = t.code;
      b.dataset.index = String(i + 1);
      b.disabled = true;
      b.title = "Apply " + typeLabel(t.code) + " to the selection (" + (TYPE_TO_DIGIT[t.code] || "") + ")";
      b.setAttribute("aria-label", "Apply " + typeLabel(t.code) + " to the selection");
      var sw = document.createElement("span");
      sw.className = "type-btn-swatch";
      sw.style.backgroundColor = t.color;
      var code = document.createElement("span");
      code.className = "type-btn-code";
      code.textContent = t.code;
      var name = document.createElement("span");
      name.className = "type-btn-name";
      name.textContent = t.name;
      var key = document.createElement("span");
      key.className = "type-btn-key";
      key.textContent = TYPE_TO_DIGIT[t.code] || "";
      b.appendChild(sw); b.appendChild(code); b.appendChild(name); b.appendChild(key);
      frag.appendChild(b);
    });
    host.appendChild(frag);
  }

  function readFilters() {
    var f = state.filters;
    f.type = E("filter-type") ? E("filter-type").value : "";
    f.family = E("filter-family") ? E("filter-family").value : "";
    f.district = E("filter-district") ? E("filter-district").value : "";
    f.ownership = E("filter-ownership") ? E("filter-ownership").value : "";
    f.use = E("filter-use") ? E("filter-use").value : "";
    f.override = E("filter-override") ? E("filter-override").value : "";
    f.pendingOnly = E("filter-pending") ? !!E("filter-pending").checked : false;
    renderAll();
  }

  var applySearch = debounce(function () {
    state.filters.search = fold(E("filter-search") ? E("filter-search").value : "");
    renderAll();
  }, 120);

  function clearFilters() {
    state.filters = { search: "", type: "", family: "", district: "", ownership: "", use: "", override: "", pendingOnly: false };
    ["filter-search", "filter-type", "filter-family", "filter-district", "filter-ownership", "filter-use", "filter-override"]
      .forEach(function (id) { var n = E(id); if (n) n.value = ""; });
    var p = E("filter-pending"); if (p) p.checked = false;
    /* The selection is work in progress; widening the view to add to it must
       not silently discard what is already picked. */
    renderAll();
  }

  /* -------------------------------------------------------- 19. wiring */

  function bindGlobal() {
    on(E("reload-btn"), "click", function () {
      if (state.pending.size) {
        openConfirm({
          title: "Discard pending changes?",
          message: "Reloading re-reads both files from disk and discards your " + state.pending.size +
            " unsaved " + plural(state.pending.size, "change") + ".",
          detail: Array.from(state.pending.keys()),
          danger: true,
          okLabel: "Discard and reload"
        }).then(function (ok) {
          if (!ok) return;
          state.pending.clear();
          lastRevert = null;
          try { sessionStorage.removeItem(PENDING_KEY); } catch (e) {}
          hideBlocking();
          loadData();
        });
      } else {
        hideBlocking();
        loadData();
      }
    });
    on(E("help-btn"), "click", function () { openDialog(E("help-dialog")); });
    on(E("help-close"), "click", function () { closeDialog(E("help-dialog")); });

    on(E("summary-types"), "click", function (e) {
      var chip = e.target.closest(".type-chip");
      if (!chip) return;
      var sel = E("filter-type");
      if (sel) { sel.value = chip.dataset.type; readFilters(); }
    });

    on(E("map-legend"), "click", function (e) {
      var item = e.target.closest(".legend-item");
      if (!item) return;
      /* "D" is a present-use record, not a Type — it has no filter-type option,
         so route it to the present-use filter instead of setting a value the
         Type <select> does not carry (which would silently clear the filter). */
      if (item.dataset.type === "D") {
        var useSel = E("filter-use");
        var typeSel = E("filter-type");
        if (typeSel) typeSel.value = "";
        if (useSel) { useSel.value = "Driveway"; readFilters(); }
        return;
      }
      var sel = E("filter-type");
      if (sel) { sel.value = item.dataset.type; readFilters(); }
    });

    /* filters */
    on(E("filter-search"), "input", applySearch);
    ["filter-type", "filter-family", "filter-district", "filter-ownership", "filter-use", "filter-override", "filter-pending"]
      .forEach(function (id) { on(E(id), "change", readFilters); });
    on(E("filter-clear"), "click", clearFilters);

    /* bulk bar */
    on(E("type-palette"), "click", function (e) {
      var b = e.target.closest("button.type-btn");
      if (!b || b.disabled) return;
      applyTypeToSelection(b.dataset.type);
    });
    on(E("bulk-ownership-apply"), "click", function () {
      var sel = E("bulk-ownership");
      if (!sel) return;
      var v = sel.value;
      if (!v) { toast("Pick an Ownership Category first.", "info"); return; }
      applyOwnershipToIds(Array.from(state.selection), v === "__blank__" ? null : v)
        .then(function () { sel.value = ""; });
    });
    on(E("bulk-use-apply"), "click", function () {
      var sel = E("bulk-use");
      if (!sel) return;
      var v = sel.value;
      if (!v) { toast("Pick a present use first.", "info"); return; }
      applyPresentUseToIds(Array.from(state.selection), v === "__blank__" ? null : v)
        .then(function () { sel.value = ""; });
    });
    on(E("bulk-exclude"), "click", function () { toggleExcludeIds(Array.from(state.selection)); });
    on(E("bulk-clear-note"), "click", function () { editNoteForIds(Array.from(state.selection)); });
    on(E("select-all"), "change", function (e) { selectAllVisible(e.target.checked); });
    on(E("selection-clear"), "click", function () { setSelection([]); });
    on(E("selection-hidden-warn"), "click", function () {
      var keep = Array.from(state.selection).filter(function (id) { return state.visibleSet.has(id); });
      var dropped = state.selection.size - keep.length;
      setSelection(keep);
      toast("Dropped " + dropped + " " + plural(dropped, "segment") +
        " the current filters hide; " + keep.length + " still selected.", "info");
    });
    on(E("selection-invert"), "click", function () {
      var next = state.visibleIds.filter(function (id) { return !state.selection.has(id); });
      setSelection(next);
    });

    /* sortable headers */
    function sortByHeader(th) {
      if (!th) return;
      var key = th.dataset.sort;
      if (state.sort.key === key) state.sort.dir = state.sort.dir === "asc" ? "desc" : "asc";
      else state.sort = { key: key, dir: "asc" };
      renderAll();
    }
    on(E("segment-head"), "click", function (e) {
      sortByHeader(e.target.closest("th[data-sort]"));
    });
    /* The headers carry tabindex="0", so they must also answer to the keyboard —
       focusable-but-inert is worse than not focusable. */
    on(E("segment-head"), "keydown", function (e) {
      if (e.key !== "Enter" && e.key !== " " && e.key !== "Spacebar") return;
      var th = e.target.closest ? e.target.closest("th[data-sort]") : null;
      if (!th) return;
      e.preventDefault();
      sortByHeader(th);
    });

    bindTable();
    bindMap();
    bindPending();
    bindDialogs();
    bindDetail();

    document.addEventListener("keydown", onKeyDown, true);
    window.addEventListener("beforeunload", function (e) {
      if (state.pending.size > 0) {
        e.preventDefault();
        e.returnValue = "";
        return "";
      }
    });
  }

  function bindTable() {
    var tbody = E("segment-tbody");
    if (!tbody) return;

    tbody.addEventListener("click", function (e) {
      var roadRow = e.target.closest("tr.road-row");
      if (roadRow) return onRoadRowClick(e, roadRow);
      var row = e.target.closest("tr.segment-row");
      if (!row) return;
      var id = row.dataset.id;

      if (e.target.closest(".seg-check")) return;                  // handled on change
      if (e.target.closest("select")) return;

      var btn = e.target.closest("button");
      if (btn) {
        if (btn.classList.contains("seg-detail-btn")) { setFocus(id); return; }
        if (btn.classList.contains("seg-note-btn")) { editNoteForIds([id]); return; }
        if (btn.classList.contains("seg-exclude-btn")) { toggleExcludeIds([id]); return; }
        return;
      }
      rowSelectGesture(e, id);
    });

    tbody.addEventListener("change", function (e) {
      var t = e.target;
      var row = t.closest("tr.segment-row");
      if (row) {
        var id = row.dataset.id;
        if (t.classList.contains("seg-check")) {
          toggleSelect(id);
          state.anchorId = id;
          setFocus(id, { scroll: false, dom: false });
          return;
        }
        if (t.classList.contains("seg-type-select")) {
          var seg = state.segById.get(id);
          var want = t.value || null;
          t.value = effType(seg);                                  // revert until staged
          applyTypeToIds([id], want);
          return;
        }
        if (t.classList.contains("seg-ownership-select")) {
          var seg2 = state.segById.get(id);
          var wantO = t.value || null;
          t.value = effOwnership(seg2);
          applyOwnershipToIds([id], wantO);
          return;
        }
        if (t.classList.contains("seg-use-select")) {
          var seg3 = state.segById.get(id);
          var wantU = t.value || null;
          t.value = effPresentUse(seg3);                           // revert until staged
          applyPresentUseToIds([id], wantU);
          return;
        }
        return;
      }
      var rr = t.closest("tr.road-row");
      if (!rr) return;
      var key = rr.dataset.roadKey;
      if (t.classList.contains("road-check")) {
        var road = state.roadByKey.get(key);
        var visIds = (road ? road.segment_ids : []).filter(function (i) { return state.visibleSet.has(i); });
        var next = new Set(state.selection);
        visIds.forEach(function (i) { if (t.checked) next.add(i); else next.delete(i); });
        setSelection(Array.from(next));
        if (visIds.length) state.anchorId = visIds[0];
        return;
      }
      if (t.classList.contains("road-type-select")) {
        var code = t.value || null;
        t.value = "";
        if (code === null) return;
        var r2 = state.roadByKey.get(key);
        if (r2) applyTypeToIds(r2.segment_ids.slice(), code);
      }
    });

    tbody.addEventListener("pointerover", function (e) {
      var row = e.target.closest("tr.segment-row");
      if (row) setHover(row.dataset.id);
    });
    tbody.addEventListener("pointerleave", function () { setHover(null); });
  }

  function onRoadRowClick(e, roadRow) {
    var key = roadRow.dataset.roadKey;
    if (e.target.closest(".road-check") || e.target.closest("select")) return;
    var btn = e.target.closest("button");
    if (btn && btn.classList.contains("road-toggle")) {
      if (state.collapsedRoads.has(key)) state.collapsedRoads.delete(key);
      else state.collapsedRoads.add(key);
      var road = state.roadByKey.get(key);
      (road ? road.segment_ids : []).forEach(function (id) {
        var row = state.rowById.get(id);
        if (row) row.hidden = state.collapsedRoads.has(key);
      });
      state.navIds = state.visibleIds.filter(function (id) {
        var s = state.segById.get(id);
        return s && !state.collapsedRoads.has(s.road_key);
      });
      renderRoadRowState(key);
      return;
    }
    if (btn && btn.classList.contains("road-zoom")) {
      var r = state.roadByKey.get(key);
      /* Zooming alone drops him into an unlabelled tangle of lines with nothing
         marking the road he asked for. Select it too, so the halo identifies it. */
      if (r) {
        setSelection(r.segment_ids.slice());
        state.anchorId = r.segment_ids[0] || null;
        if (r.segment_ids[0]) setFocus(r.segment_ids[0], { scroll: false, dom: false });
        zoomToIds(r.segment_ids);
      }
      return;
    }
    /* clicking the road name selects the whole road (visible part) */
    var road2 = state.roadByKey.get(key);
    if (road2) {
      var ids = road2.segment_ids.filter(function (i) { return state.visibleSet.has(i); });
      setSelection(ids);
      state.anchorId = ids[0] || null;
      if (ids[0]) setFocus(ids[0], { scroll: false, dom: false });
    }
  }

  function rowSelectGesture(e, id) {
    if (e.shiftKey && state.anchorId) {
      selectRange(id);
      setFocus(id, { scroll: false, dom: false });
    } else if (e.metaKey || e.ctrlKey) {
      toggleSelect(id);
      state.anchorId = id;
      setFocus(id, { scroll: false, dom: false });
    } else {
      setSelection([id]);
      state.anchorId = id;
      setFocus(id, { scroll: false, dom: false });
    }
  }

  /* The visible line and its transparent fat twin both answer to the same id. */
  function mapSegIdFromEvent(e) {
    var n = e.target && e.target.closest ? e.target.closest("path.map-hit, path.map-seg") : null;
    return n ? n.dataset.id : null;
  }

  function bindMap() {
    var svg = E("map");
    if (!svg) return;

    svg.addEventListener("pointerover", function (e) {
      var id = mapSegIdFromEvent(e);
      if (id) setHover(id, { scrollRow: true });
    });
    svg.addEventListener("pointerleave", function () { setHover(null); });

    svg.addEventListener("click", function (e) {
      var id = mapSegIdFromEvent(e);
      if (!id) return;
      rowSelectGesture(e, id);
      setFocus(id, { scroll: true, dom: false });
    });

    svg.addEventListener("wheel", function (e) {
      e.preventDefault();
      var pt = svgPoint(e);
      if (!pt) return;
      zoomAbout(pt[0], pt[1], e.deltaY < 0 ? 1.18 : 1 / 1.18);
    }, { passive: false });

    var dragging = false, last = null;
    svg.addEventListener("pointerdown", function (e) {
      if (e.button !== 0) return;
      if (mapSegIdFromEvent(e)) return;                                  // clicking a line selects
      dragging = true; last = svgPoint(e);
      svg.classList.add("is-panning");
      if (svg.setPointerCapture) { try { svg.setPointerCapture(e.pointerId); } catch (err) {} }
    });
    svg.addEventListener("pointermove", function (e) {
      if (!dragging) return;
      var pt = svgPoint(e);
      if (!pt || !last) return;
      /* svgPoint() already reports the OUTER viewBox system, which is the same
         system tx/ty live in. Keeping the grabbed point under the cursor is
         therefore Δt = Δp exactly — scaling by k threw the map k viewBox-widths
         per drag and made panning unusable at the zoom levels that need it. */
      state.zoom.tx += pt[0] - last[0];
      state.zoom.ty += pt[1] - last[1];
      clampPan();
      applyZoom();
      last = svgPoint(e);
    });
    ["pointerup", "pointercancel", "pointerleave"].forEach(function (ev) {
      svg.addEventListener(ev, function () { dragging = false; last = null; svg.classList.remove("is-panning"); });
    });

    on(E("map-zoom-in"), "click", function () {
      var v = state.view;
      zoomAbout(v ? v.vbw / 2 : 500, v ? v.vbh / 2 : 500, 1.4);
    });
    on(E("map-zoom-out"), "click", function () {
      var v = state.view;
      zoomAbout(v ? v.vbw / 2 : 500, v ? v.vbh / 2 : 500, 1 / 1.4);
    });
    on(E("map-zoom-reset"), "click", resetZoom);
    /* styles.css has carried .is-stacked since the first pass, but nothing ever
       set it, so there was no way to escape the ~200 px rail. */
    on(E("map-expand"), "click", function () {
      var panel = E("map-panel");
      if (!panel) return;
      var nowStacked = !panel.classList.contains("is-stacked");
      panel.classList.toggle("is-stacked", nowStacked);
      var btn = E("map-expand");
      if (btn) {
        btn.setAttribute("aria-pressed", String(nowStacked));
        btn.textContent = nowStacked ? "Collapse" : "Expand";
        btn.title = nowStacked
          ? "Put the map back beside the table"
          : "Give the map the full width of the window";
      }
    });
    on(E("map-dim-filtered"), "change", function (e) {
      state.dimFiltered = !!e.target.checked;
      applyMapFilterClasses();
    });
    var dim = E("map-dim-filtered");
    if (dim) state.dimFiltered = !!dim.checked;
  }

  function bindPending() {
    on(E("pending-list"), "click", function (e) {
      var li = e.target.closest("li.pending-item");
      if (!li) return;
      var id = li.dataset.id;
      var btn = e.target.closest("button");
      if (!btn) { setFocus(id); return; }
      if (btn.classList.contains("pending-revert")) { revert(id); return; }
      if (btn.classList.contains("pending-note-edit")) { editNoteForIds([id]); return; }
      if (btn.classList.contains("pending-locate")) {
        if (state.segById.has(id)) { setSelection([id]); state.anchorId = id; }
        setFocus(id);
        zoomToIds([id]);
        return;
      }
    });
    on(E("pending-clear"), "click", function () {
      if (!state.pending.size) return;
      openConfirm({
        title: "Revert all pending changes?",
        message: "This discards " + state.pending.size + " staged " + plural(state.pending.size, "change") +
          ". Nothing on disk is touched.",
        detail: Array.from(state.pending.keys()),
        danger: true,
        okLabel: "Revert all"
      }).then(function (ok) { if (ok) revertAll(); });
    });
    on(E("validate-btn"), "click", doValidate);
    on(E("save-btn"), "click", doSave);
    on(E("apply-inventory"), "change", function () { setSaveStatus("idle", ""); });

    var overlay = E("blocking-overlay");
    if (overlay) {
      overlay.addEventListener("click", function (e) { if (e.target === overlay) hideBlocking(); });
    }
    /* Backdrop-click and Escape both dismiss, but neither is discoverable and
       the overlay's copy promises a way out. */
    on(E("blocking-dismiss"), "click", hideBlocking);
  }

  function bindDetail() {
    on(E("detail-neighbors"), "click", function (e) {
      var b = e.target.closest("[data-id]");
      if (!b) return;
      setFocus(b.dataset.id);
      setSelection([b.dataset.id]);
      state.anchorId = b.dataset.id;
    });
    on(E("detail-note-btn"), "click", function () {
      if (state.focusId) editNoteForIds([state.focusId]);
    });
    on(E("detail-exclude-btn"), "click", function () {
      if (state.focusId) toggleExcludeIds([state.focusId]);
    });
    on(E("detail-delete-btn"), "click", function () {
      if (state.focusId) confirmDeleteOverride(state.focusId);
    });
    on(E("detail-row-ft"), "change", function (e) { stageNumeric("row_ft", e.target); });
    on(E("detail-traveled-ft"), "change", function (e) { stageNumeric("traveled_ft", e.target); });
    on(E("detail-nonconformity"), "change", function (e) {
      if (!state.focusId) return;
      var v = e.target.value.trim();
      stageWithNote([state.focusId], { nonconformity: v ? v : null }, { toast: false });
    });
  }

  function stageNumeric(field, input) {
    if (!state.focusId) return;
    var raw = input.value.trim();
    if (raw === "") { stageWithNote([state.focusId], defineField(field, null), { toast: false }); return; }
    var n = Number(raw);
    if (!isFinite(n) || n <= 0 || n > 1000) {
      toast(FIELD_LABEL[field] + " must be a number greater than 0 and at most 1000.", "error");
      renderDetail();
      return;
    }
    stageWithNote([state.focusId], defineField(field, Math.round(n * 100) / 100), { toast: false });
  }
  function defineField(field, value) { var o = {}; o[field] = value; return o; }

  function bindDialogs() {
    var note = E("note-dialog");
    if (note) {
      on(E("note-confirm"), "click", function (e) {
        e.preventDefault();
        var input = E("note-input");
        var v = input ? input.value.trim() : "";
        persistAutoNotePref();
        settleNote({ note: v || null });
      });
      on(E("note-keep-btn"), "click", function (e) {
        e.preventDefault();
        persistAutoNotePref();
        settleNote({ note: null });
      });
      on(E("note-cancel"), "click", function (e) { e.preventDefault(); settleNote(null); });
      on(E("note-suggest-btn"), "click", function (e) {
        e.preventDefault();
        var input = E("note-input");
        if (input) { input.value = input.dataset.generated || ""; input.focus(); input.select(); }
      });
      note.addEventListener("cancel", function (e) { e.preventDefault(); settleNote(null); });
      note.addEventListener("close", function () { if (noteResolve) settleNote(null); });
      note.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
          e.preventDefault();
          var input = E("note-input");
          persistAutoNotePref();
          settleNote({ note: input ? (input.value.trim() || null) : null });
        }
      });
    }
    var conf = E("confirm-dialog");
    if (conf) {
      on(E("confirm-ok"), "click", function (e) { e.preventDefault(); settleConfirm(true); });
      on(E("confirm-cancel"), "click", function (e) { e.preventDefault(); settleConfirm(false); });
      conf.addEventListener("cancel", function (e) { e.preventDefault(); settleConfirm(false); });
      conf.addEventListener("close", function () { if (confirmResolve) settleConfirm(false); });
    }
    var help = E("help-dialog");
    if (help) {
      help.addEventListener("cancel", function () { /* native close is fine */ });
    }
    on(E("toast-container"), "click", function (e) {
      var b = e.target.closest(".toast-close");
      if (b) { var t = b.closest(".toast"); if (t) t.remove(); }
    });
  }

  function persistAutoNotePref() {
    var pref = E("pref-auto-note");
    if (!pref) return;
    state.autoNote = !!pref.checked;
    try { localStorage.setItem(AUTO_NOTE_KEY, state.autoNote ? "1" : "0"); } catch (e) { /* private mode */ }
  }

  /* ------------------------------------------------------ 20. keyboard */

  var chord = { prefix: null, timer: 0 };

  function setChord(prefix) {
    chord.prefix = prefix;
    var hint = E("shortcut-hint");
    if (hint) {
      hint.textContent = prefix ? prefix + "…" : "";
      hint.hidden = !prefix;
    }
    if (chord.timer) clearTimeout(chord.timer);
    if (prefix) chord.timer = setTimeout(function () { setChord(null); }, 1500);
  }

  function isTypingTarget(t) {
    if (!t) return false;
    var tag = (t.tagName || "").toLowerCase();
    return tag === "input" || tag === "textarea" || tag === "select" || t.isContentEditable;
  }

  function onKeyDown(e) {
    var meta = e.metaKey || e.ctrlKey;

    if (meta && (e.key === "s" || e.key === "S")) {
      e.preventDefault();
      doSave();
      return;
    }
    if (e.key === "Escape") {
      if (anyDialogOpen()) return;                     // the dialog's own handler deals with it
      var overlay = E("blocking-overlay");
      if (overlay && !overlay.hidden) { hideBlocking(); return; }
      if (chord.prefix) { setChord(null); return; }
      if (state.selection.size) { setSelection([]); return; }
      var search = E("filter-search");
      if (document.activeElement === search) { search.blur(); return; }
      return;
    }
    if (anyDialogOpen()) return;

    if (meta && (e.key === "k" || e.key === "K")) {
      e.preventDefault();
      focusSearch();
      return;
    }
    if (meta && (e.key === "z" || e.key === "Z")) {
      if (isTypingTarget(e.target)) return;
      e.preventDefault();
      revertLast();
      return;
    }
    if (isTypingTarget(e.target)) return;
    if (meta || e.altKey) return;

    var k = e.key;

    if (chord.prefix && /^[1-5]$/.test(k)) {
      e.preventDefault();
      applyTypeToSelection(chord.prefix + k);
      setChord(null);
      return;
    }

    switch (k) {
      case "/":
        e.preventDefault(); focusSearch(); return;
      case "?":
        e.preventDefault(); openDialog(E("help-dialog")); return;
      case "s": case "S":
        e.preventDefault(); setChord("S"); return;
      case "r": case "R":
        e.preventDefault(); setChord("R"); return;
      case "j":
        e.preventDefault(); moveFocus(1, e.shiftKey); return;
      case "k":
        e.preventDefault(); moveFocus(-1, e.shiftKey); return;
      case "ArrowDown":
        e.preventDefault(); moveFocus(1, e.shiftKey); return;
      case "ArrowUp":
        e.preventDefault(); moveFocus(-1, e.shiftKey); return;
      case " ":
        if (state.focusId) { e.preventDefault(); toggleSelect(state.focusId); state.anchorId = state.focusId; }
        return;
      case "a": case "A":
        e.preventDefault(); selectAllVisible(true); return;
      case "x": case "X":
        e.preventDefault(); toggleExcludeIds(Array.from(state.selection)); return;
      case "n": case "N":
        e.preventDefault();
        editNoteForIds(state.selection.size ? Array.from(state.selection) : (state.focusId ? [state.focusId] : []));
        return;
      case "Delete": case "Backspace":
        /* Not in §10 — additive: removes the whole override entry for the focused
           segment. Also on #detail-delete-btn in the inspector. */
        if (e.shiftKey && state.focusId) {
          e.preventDefault();
          confirmDeleteOverride(state.focusId);
        }
        return;
    }

    if (/^[0-9]$/.test(k) && DIGIT_TO_TYPE[k]) {
      e.preventDefault();
      applyTypeToSelection(DIGIT_TO_TYPE[k]);
      setChord(null);
    }
  }

  function focusSearch() {
    var s = E("filter-search");
    if (!s) return;
    s.focus();
    s.select();
  }

  /* ----------------------------------------------------------- 21. boot */

  function init() {
    try { state.autoNote = localStorage.getItem(AUTO_NOTE_KEY) === "1"; } catch (e) { state.autoNote = false; }
    var pref = E("pref-auto-note");
    if (pref) pref.checked = state.autoNote;
    var apply = E("apply-inventory");
    if (apply && !apply.hasAttribute("checked")) apply.checked = true;   // default ON (§8.5)

    setSaveStatus("idle", "");
    renderSaveControls();
    bindGlobal();
    loadData({ reset: true }).catch(function () { /* toast already shown */ });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();

  /* A tiny console handle for the one action the DOM contract has no button for,
     plus read-only introspection while working. Never used by the UI itself. */
  window.__nczcEditor = {
    state: state,
    stageDelete: stageDelete,
    reload: loadData,
    generateNote: generateNote
  };
})();
