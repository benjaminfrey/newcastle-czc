// Newcastle Permit Review — the live meeting workflow (W7).
// Vanilla JS only, no npm, no build step (CONTRACT.md §8), matching
// case-detail.js's own idiom exactly (postJSON/showResult shape).
//
// THE FRAMING RULE, in this file specifically: this script never renders a
// pre-selected outcome, never defaults a vote tally, and never states a
// conclusion the agenda JSON did not already report as a recorded human
// act. Every "Carried/Failed/Tabled/Withdrawn" choice starts unselected;
// every Yea/Nay/Abstain field starts empty, not zero.

(function () {
  "use strict";

  function $(id) { return document.getElementById(id); }
  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (k) {
      if (k === "class") node.className = attrs[k];
      else if (k === "text") node.textContent = attrs[k];
      else if (k === "html") node.innerHTML = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { if (c) node.appendChild(c); });
    return node;
  }

  function requestJSON(url, method, body) {
    var opts = { method: method, headers: {} };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(url, opts).then(function (resp) {
      return resp.json().then(function (json) { return { status: resp.status, json: json }; });
    });
  }

  function errorText(result) {
    var msg = (result.json && (result.json.message || result.json.error)) || "Request failed.";
    if (result.json && result.json.details) {
      msg += " " + JSON.stringify(result.json.details);
    }
    return msg;
  }

  var header = $("meeting-header");
  if (!header) return; // module loaded on a page without the meeting screen
  var CASE_ID = header.getAttribute("data-case-id");
  var API = "/api/cases/" + encodeURIComponent(CASE_ID) + "/meeting";

  var errorBanner = $("meeting-error");
  function showBanner(msg) {
    if (!msg) { errorBanner.hidden = true; errorBanner.textContent = ""; return; }
    errorBanner.hidden = false;
    errorBanner.textContent = msg;
  }

  // ------------------------------------------------------------------- //
  // State
  // ------------------------------------------------------------------- //

  var state = {
    agenda: null,
    items: [],       // flattened agenda rows, in display order
    selected: 0,      // index into items, the highlighted row
    openIndex: -1,    // index whose detail panel is currently rendered
  };

  function outcomeLabel(o) {
    return { carried: "Carried", failed: "Failed", tabled: "Tabled", withdrawn: "Withdrawn" }[o] || o;
  }

  // ------------------------------------------------------------------- //
  // Build the flattened item list from one agenda JSON payload.
  // ------------------------------------------------------------------- //

  function computeItems(agenda) {
    var items = [];
    items.push({
      type: "disclosures", key: "disclosures",
      label: "Conflict of Interest Disclosures",
      resolved: agenda.disclosures_resolved,
    });
    items.push({
      type: "completeness", key: "completeness",
      label: "Completeness Determination",
      motion: agenda.completeness_motion,
      resolved: !!(agenda.completeness_motion && agenda.completeness_motion.outcome),
    });
    agenda.standards.forEach(function (s) {
      items.push({
        type: "standard", key: "standard:" + s.node_id,
        label: (s.number_label ? s.number_label + " " : "") + (s.heading || "Standard"),
        standard: s, motion: s.motion, resolved: s.resolved,
      });
    });
    if (agenda.conditions_applicable) {
      items.push({
        type: "conditions", key: "conditions",
        label: "Conditions of Approval Vote",
        motion: agenda.conditions_motion,
        resolved: !!(agenda.conditions_motion && agenda.conditions_motion.outcome),
      });
    }
    items.push({
      type: "adoption", key: "adoption",
      label: "Adoption of Findings of Fact & Conclusions of Law",
      motion: agenda.adoption_motion,
      resolved: !!(agenda.adoption_motion && agenda.adoption_motion.outcome),
    });
    items.push({
      type: "decision", key: "decision",
      label: "Board Decision (Outcome)",
      motion: agenda.decision_motion, decision: agenda.decision,
      resolved: !!agenda.decision,
    });
    return items;
  }

  // ------------------------------------------------------------------- //
  // Fetch + refresh
  // ------------------------------------------------------------------- //

  function loadAgenda(preserveOpen) {
    return requestJSON(API + "/agenda", "GET").then(function (result) {
      if (result.status !== 200 || !result.json.ok) {
        showBanner(errorText(result));
        return;
      }
      showBanner(null);
      state.agenda = result.json.data;
      var prevKey = state.items[state.selected] ? state.items[state.selected].key : null;
      var openKey = preserveOpen && state.items[state.openIndex] ? state.items[state.openIndex].key : null;
      state.items = computeItems(state.agenda);
      var idx = prevKey ? state.items.findIndex(function (it) { return it.key === prevKey; }) : -1;
      state.selected = idx >= 0 ? idx : 0;
      state.openIndex = openKey ? state.items.findIndex(function (it) { return it.key === openKey; }) : -1;
      render();
    }).catch(function (e) { showBanner("Request failed: " + e); });
  }

  function prepareThenLoad() {
    requestJSON(API + "/prepare", "POST").then(function (result) {
      if (result.status !== 200 || !result.json.ok) {
        showBanner(errorText(result));
      }
      loadAgenda(false);
    }).catch(function () { loadAgenda(false); });
  }

  // ------------------------------------------------------------------- //
  // Render: status bar + agenda list
  // ------------------------------------------------------------------- //

  function render() {
    var counts = state.agenda.counts;
    $("status-position").textContent = state.items.length ? (state.selected + 1) + " / " + state.items.length : "—";
    $("status-unresolved").textContent = counts.unresolved;
    $("status-resolved").textContent = counts.resolved + " / " + counts.total;

    var list = $("agenda-list");
    list.innerHTML = "";
    state.items.forEach(function (item, i) {
      var classes = "agenda-item" + (item.resolved ? " agenda-item-resolved" : " agenda-item-unresolved")
        + (i === state.selected ? " agenda-item-selected" : "")
        + (i === state.openIndex ? " agenda-item-open" : "");
      var li = el("li", { class: classes, "data-index": String(i) }, [
        el("span", { class: "agenda-item-mark", text: item.resolved ? "✓" : "○" }),
        el("span", { class: "agenda-item-label", text: item.label }),
      ]);
      li.addEventListener("click", function () { selectIndex(i); openSelected(); });
      list.appendChild(li);
    });

    if (state.openIndex >= 0 && state.items[state.openIndex]) {
      renderDetail(state.items[state.openIndex]);
    }
    scrollSelectedIntoView();
  }

  function scrollSelectedIntoView() {
    var row = document.querySelector('.agenda-item[data-index="' + state.selected + '"]');
    if (row && row.scrollIntoView) row.scrollIntoView({ block: "nearest" });
  }

  function selectIndex(i) {
    if (!state.items.length) return;
    state.selected = Math.max(0, Math.min(state.items.length - 1, i));
    render();
  }

  function openSelected() {
    state.openIndex = state.selected;
    render();
  }

  function closeDetail() {
    state.openIndex = -1;
    render();
    var detail = $("meeting-detail");
    detail.innerHTML = "";
    detail.appendChild(el("p", {
      class: "notice",
      html: 'Select an agenda item (<kbd>j</kbd>/<kbd>k</kbd>, then <kbd>Enter</kbd>) to record disclosures, votes, or amendments.',
    }));
  }

  function jumpToNextUnresolved() {
    for (var i = 0; i < state.items.length; i++) {
      var idx = (state.selected + 1 + i) % state.items.length;
      if (!state.items[idx].resolved) { selectIndex(idx); openSelected(); return; }
    }
  }

  // ------------------------------------------------------------------- //
  // Board-member <select> options, shared by every vote form.
  // ------------------------------------------------------------------- //

  function fillMemberSelect(select, current) {
    select.innerHTML = "";
    select.appendChild(el("option", { value: "", text: "— choose —" }));
    (state.agenda.board_members || []).forEach(function (m) {
      var label = m.name + (m.seat ? " (" + m.seat + ")" : "");
      var opt = el("option", { value: m.board_member_id, text: label });
      if (current && current === m.board_member_id) opt.selected = true;
      select.appendChild(opt);
    });
  }

  // ------------------------------------------------------------------- //
  // The generic vote form (completeness / standard / conditions / adoption
  // / decision all share this shape: moved_by, seconded_by, tallies, one
  // of four outcomes, optional discussion).
  // ------------------------------------------------------------------- //

  function buildVoteForm(container, item, opts) {
    opts = opts || {};
    var tmpl = $("tmpl-vote-form");
    var frag = tmpl.content.cloneNode(true);
    var form = frag.querySelector("[data-role='vote-form']");
    var motion = item.motion;

    form.querySelector("[data-field='motion-text']").textContent = motion ? motion.text : "(no motion drafted yet)";

    var movedSel = form.querySelector("[data-field='moved_by']");
    var secondSel = form.querySelector("[data-field='seconded_by']");
    fillMemberSelect(movedSel, motion ? motion.moved_by : null);
    fillMemberSelect(secondSel, motion ? motion.seconded_by : null);

    var yesInput = form.querySelector("[name='votes_yes']");
    var noInput = form.querySelector("[name='votes_no']");
    var abstainInput = form.querySelector("[name='votes_abstain']");
    if (motion) {
      if (motion.votes_yes !== null && motion.votes_yes !== undefined) yesInput.value = motion.votes_yes;
      if (motion.votes_no !== null && motion.votes_no !== undefined) noInput.value = motion.votes_no;
      if (motion.votes_abstain !== null && motion.votes_abstain !== undefined) abstainInput.value = motion.votes_abstain;
      if (motion.discussion) form.querySelector("[name='discussion']").value = motion.discussion;
      if (motion.outcome) {
        var radio = form.querySelector('input[name="outcome"][value="' + motion.outcome + '"]');
        if (radio) radio.checked = true;
      }
    }

    if (opts.conclusionNote) {
      var note = form.querySelector("[data-field='conclusion-note']");
      note.hidden = false;
      note.textContent = opts.conclusionNote;
    }

    if (!motion) {
      form.querySelectorAll("input, select, textarea, button[type=submit]").forEach(function (f) { f.disabled = true; });
      var resultEl = form.querySelector("[data-field='vote-result']");
      resultEl.textContent = "Draft the motion first.";
    }

    var resultSpan = form.querySelector("[data-field='vote-result']");

    form.addEventListener("submit", function (evt) {
      evt.preventDefault();
      if (!motion) return;
      var outcomeEl = form.querySelector('input[name="outcome"]:checked');
      if (!outcomeEl) {
        resultSpan.className = "render-result error";
        resultSpan.textContent = "Choose a result (carried/failed/tabled/withdrawn).";
        return;
      }
      var payload = {
        moved_by: movedSel.value || null,
        seconded_by: secondSel.value || null,
        votes_yes: yesInput.value === "" ? null : parseInt(yesInput.value, 10),
        votes_no: noInput.value === "" ? null : parseInt(noInput.value, 10),
        votes_abstain: abstainInput.value === "" ? null : parseInt(abstainInput.value, 10),
        outcome: outcomeEl.value,
        discussion: form.querySelector("[name='discussion']").value || null,
      };
      resultSpan.className = "render-result";
      resultSpan.textContent = "Saving…";
      requestJSON(API + "/motions/" + encodeURIComponent(motion.id), "PATCH", payload).then(function (result) {
        if (result.status !== 200 || !result.json.ok) {
          resultSpan.className = "render-result error";
          resultSpan.textContent = errorText(result);
          return;
        }
        resultSpan.className = "render-result success";
        var extra = "";
        if (result.json.data.apply_error) extra = " (could not apply: " + result.json.data.apply_error + ")";
        resultSpan.textContent = "Recorded." + extra;
        loadAgenda(true);
      }).catch(function (e) {
        resultSpan.className = "render-result error";
        resultSpan.textContent = "Request failed: " + e;
      });
    });

    container.appendChild(form);
    return form;
  }

  // ------------------------------------------------------------------- //
  // Per-item detail renderers
  // ------------------------------------------------------------------- //

  function renderDisclosures(container, item) {
    container.appendChild(el("h3", { text: item.label }));
    container.appendChild(el("p", { class: "muted",
      text: "Absence of a record is not a finding of “no conflicts” — every member must be recorded." }));
    var table = el("table", {}, [
      el("thead", {}, [el("tr", {}, [
        el("th", { text: "Member" }), el("th", { text: "Status" }),
        el("th", { text: "Discloses a conflict?" }), el("th", { text: "Recused?" }),
        el("th", { text: "Nature (if disclosed)" }), el("th", { text: "" }),
      ])]),
    ]);
    var tbody = el("tbody");
    (state.agenda.disclosures || []).forEach(function (d) {
      var natureInput = el("input", { type: "text", value: d.nature || "", placeholder: "nature of the conflict" });
      var recusedBox = el("input", { type: "checkbox" });
      recusedBox.checked = !!d.recused;
      var discloseYes = el("input", { type: "radio", name: "disc-" + d.board_member_id, value: "yes" });
      var discloseNo = el("input", { type: "radio", name: "disc-" + d.board_member_id, value: "no" });
      if (d.recorded) { (d.disclosed ? discloseYes : discloseNo).checked = true; }
      var statusText = !d.recorded ? "TBD…" : (d.disclosed ? "Disclosed" : "No conflict");
      var resultCell = el("span", { class: "render-result" });
      var saveBtn = el("button", { type: "button", text: d.recorded ? "Update" : "Record" });
      saveBtn.addEventListener("click", function () {
        if (!discloseYes.checked && !discloseNo.checked) {
          resultCell.className = "render-result error";
          resultCell.textContent = "Choose yes or no.";
          return;
        }
        resultCell.className = "render-result";
        resultCell.textContent = "Saving…";
        requestJSON(API + "/disclosures", "POST", {
          board_member_id: d.board_member_id,
          disclosed: discloseYes.checked,
          recused: recusedBox.checked,
          nature: natureInput.value || null,
        }).then(function (result) {
          if (result.status !== 200 || !result.json.ok) {
            resultCell.className = "render-result error";
            resultCell.textContent = errorText(result);
            return;
          }
          loadAgenda(true);
        });
      });
      var tr = el("tr", {}, [
        el("td", { text: d.name + (d.is_chair ? " (Chair)" : "") }),
        el("td", { text: statusText, class: d.recorded ? "" : "muted" }),
        el("td", {}, [
          el("label", { class: "checkbox-label" }, [discloseYes, document.createTextNode(" yes")]),
          el("label", { class: "checkbox-label" }, [discloseNo, document.createTextNode(" no")]),
        ]),
        el("td", {}, [recusedBox]),
        el("td", {}, [natureInput]),
        el("td", {}, [saveBtn, resultCell]),
      ]);
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    container.appendChild(table);
    if (!(state.agenda.board_members || []).length) {
      container.appendChild(el("p", { class: "notice notice-warn",
        text: "No sitting board members are on file yet." }));
    }
  }

  function renderCompleteness(container, item) {
    container.appendChild(el("h3", { text: item.label }));
    buildVoteForm(container, item);
  }

  function renderStandard(container, item) {
    var s = item.standard;
    container.appendChild(el("h3", { text: item.label }));
    if (s.citation_text) container.appendChild(el("p", { class: "field-citation", text: s.citation_text }));
    if (s.board_question) container.appendChild(el("p", { class: "board-question", text: s.board_question }));
    if (s.applicability_verdict === "unknown") {
      container.appendChild(el("p", { class: "notice notice-warn",
        text: "Applicability could not be determined by the engine — the Board must decide whether this standard applies." }));
    }
    if (s.conclusion) {
      container.appendChild(el("p", { class: "notice-finding",
        text: "Recorded conclusion: " + s.conclusion.toUpperCase().replace("_", " ") + " (set by a carried vote)." }));
    }

    var amendBtn = el("button", { type: "button", class: "btn-secondary", text: "Amend this finding (a)" });
    var amendResult = el("span", { class: "render-result" });
    amendBtn.addEventListener("click", function () { openAmendForm(container, item, amendBtn, amendResult); });
    container.appendChild(el("div", { class: "actions-row" }, [amendBtn, amendResult]));

    if (s.conclusion) {
      container.appendChild(el("p", { class: "notice",
        text: "This standard already carries a Board-recorded conclusion; it can no longer be amended or re-voted here." }));
      return;
    }

    buildVoteForm(container, item, {
      conclusionNote: "Carrying this motion records this standard as MET. Failing it records NOT MET. " +
        "Tabling or withdrawing leaves it unresolved for a future motion.",
    });
  }

  function openAmendForm(container, item, triggerBtn, resultEl) {
    if (container.querySelector(".amend-form")) return;
    var bodyInput = el("textarea", { rows: "3", placeholder: "Corrected finding text (optional)" });
    var whyInput = el("input", { type: "text", placeholder: "Why is this being amended? (required)", required: "required" });
    var saveBtn = el("button", { type: "button", text: "Save amendment" });
    var cancelBtn = el("button", { type: "button", class: "btn-secondary", text: "Cancel" });
    var localResult = el("span", { class: "render-result" });
    var form = el("div", { class: "amend-form" }, [
      el("label", { class: "field-why-label" }, [document.createTextNode("Corrected finding"), bodyInput]),
      el("label", { class: "field-why-label" }, [document.createTextNode("Why (required)"), whyInput]),
      el("div", { class: "actions-row" }, [saveBtn, cancelBtn, localResult]),
    ]);
    saveBtn.addEventListener("click", function () {
      if (!whyInput.value || !whyInput.value.trim()) {
        localResult.className = "render-result error";
        localResult.textContent = "A reason is required — an amendment must state why.";
        whyInput.focus();
        return;
      }
      var payload = { why: whyInput.value };
      if (bodyInput.value.trim()) payload.body = bodyInput.value.trim();
      localResult.className = "render-result";
      localResult.textContent = "Saving…";
      requestJSON(API + "/nodes/" + encodeURIComponent(item.standard.node_id) + "/amend", "POST", payload)
        .then(function (result) {
          if (result.status !== 200 || !result.json.ok) {
            localResult.className = "render-result error";
            localResult.textContent = errorText(result);
            return;
          }
          loadAgenda(true);
        });
    });
    cancelBtn.addEventListener("click", function () { form.remove(); });
    container.insertBefore(form, triggerBtn.parentElement.nextSibling);
    whyInput.focus();
  }

  function renderConditions(container, item) {
    container.appendChild(el("h3", { text: item.label }));
    var ul = el("ul");
    (state.agenda.conditions || []).forEach(function (c) {
      ul.appendChild(el("li", { text: (c.number_label ? c.number_label + ". " : "") + c.text + " [" + c.status + "]" }));
    });
    container.appendChild(ul);
    buildVoteForm(container, item);
  }

  function renderAdoption(container, item) {
    container.appendChild(el("h3", { text: item.label }));
    var incompleteCount = state.items.filter(function (it) {
      return it.type !== "adoption" && it.type !== "decision" && !it.resolved;
    }).length;
    if (incompleteCount > 0) {
      container.appendChild(el("p", { class: "notice notice-warn",
        text: incompleteCount + " earlier agenda item(s) are not yet resolved. The Chair may still proceed " +
          "— this app never blocks the Board’s own process — but nothing here implies they are done." }));
    }
    if (!item.motion) {
      var draftBtn = el("button", { type: "button", text: "Draft the adoption motion (verbatim wording)" });
      var draftResult = el("span", { class: "render-result" });
      draftBtn.addEventListener("click", function () {
        requestJSON(API + "/motions", "POST", { kind: "adoption" }).then(function (result) {
          if (result.status !== 200 || !result.json.ok) {
            draftResult.className = "render-result error";
            draftResult.textContent = errorText(result);
            return;
          }
          loadAgenda(true);
        });
      });
      container.appendChild(el("div", { class: "actions-row" }, [draftBtn, draftResult]));
      return;
    }
    buildVoteForm(container, item);
  }

  var DISPOSITIONS = [
    ["approve", "Approve"],
    ["approve_with_conditions", "Approve, with conditions"],
    ["deny", "Deny"],
    ["table", "Table (continue to a future meeting)"],
    ["withdraw", "Accept withdrawal"],
  ];

  function renderDecision(container, item) {
    container.appendChild(el("h3", { text: item.label }));
    if (item.decision) {
      container.appendChild(el("p", { class: "notice-finding",
        text: "Recorded decision: " + item.decision.outcome.toUpperCase().replace(/_/g, " ") +
          " (decided " + (item.decision.decided_at || "") + ")." }));
      renderAdoptedFinalPanel(container);
      return;
    }

    var pickerRow = el("div", { class: "actions-row" });
    var pickResult = el("span", { class: "render-result" });
    DISPOSITIONS.forEach(function (pair) {
      var btn = el("button", { type: "button", class: "btn-secondary", text: pair[1] });
      btn.addEventListener("click", function () {
        pickResult.className = "render-result";
        pickResult.textContent = "Drafting…";
        requestJSON(API + "/motions", "POST", { kind: "decision", disposition: pair[0] }).then(function (result) {
          if (result.status !== 200 || !result.json.ok) {
            pickResult.className = "render-result error";
            pickResult.textContent = errorText(result);
            return;
          }
          loadAgenda(true);
        });
      });
      pickerRow.appendChild(btn);
    });
    pickerRow.appendChild(pickResult);
    container.appendChild(el("p", { class: "vote-form-label", text: "Draft (or re-draft) the decision motion:" }));
    container.appendChild(pickerRow);

    if (item.motion) {
      buildVoteForm(container, item, {
        conclusionNote: "Carrying this motion records the Board's disposition of the case.",
      });
    }
  }

  function renderAdoptedFinalPanel(container) {
    var btn = el("button", { type: "button", text: "Produce Adopted Final" });
    var result = el("span", { class: "render-result" });
    btn.addEventListener("click", function () {
      result.className = "render-result";
      result.textContent = "Rendering…";
      requestJSON("/api/cases/" + encodeURIComponent(CASE_ID) + "/findings/adopt", "POST").then(function (r) {
        if (r.status !== 200 || !r.json.ok) {
          result.className = "render-result error";
          result.textContent = errorText(r);
          return;
        }
        result.className = "render-result success";
        result.textContent = "Adopted final produced: " + r.json.data.path;
      }).catch(function (e) {
        result.className = "render-result error";
        result.textContent = "Request failed: " + e;
      });
    });
    container.appendChild(el("div", { class: "actions-row" }, [btn, result]));
  }

  var RENDERERS = {
    disclosures: renderDisclosures,
    completeness: renderCompleteness,
    standard: renderStandard,
    conditions: renderConditions,
    adoption: renderAdoption,
    decision: renderDecision,
  };

  function renderDetail(item) {
    var container = $("meeting-detail");
    container.innerHTML = "";
    var renderer = RENDERERS[item.type];
    if (renderer) renderer(container, item);
  }

  // ------------------------------------------------------------------- //
  // Keyboard bindings
  // ------------------------------------------------------------------- //

  function isTyping() {
    var a = document.activeElement;
    if (!a) return false;
    var tag = a.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
  }

  function toggleHelp(show) {
    var overlay = $("help-overlay");
    overlay.hidden = show === undefined ? !overlay.hidden : !show;
  }

  document.addEventListener("keydown", function (evt) {
    var overlay = $("help-overlay");
    if (!overlay.hidden) {
      if (evt.key === "Escape" || evt.key === "?") { toggleHelp(false); evt.preventDefault(); }
      return;
    }

    // Ctrl/Cmd+Enter submits the open vote form regardless of focus.
    if ((evt.metaKey || evt.ctrlKey) && evt.key === "Enter") {
      var openForm = document.querySelector("#meeting-detail form[data-role='vote-form']");
      if (openForm) { openForm.requestSubmit ? openForm.requestSubmit() : openForm.dispatchEvent(new Event("submit", { cancelable: true })); evt.preventDefault(); }
      return;
    }

    if (evt.key === "Escape") {
      if (state.openIndex >= 0) { closeDetail(); evt.preventDefault(); }
      return;
    }

    if (isTyping()) return; // never hijack ordinary typing

    if (evt.key === "?") { toggleHelp(true); evt.preventDefault(); return; }
    if (evt.key === "j" || evt.key === "ArrowDown") { selectIndex(state.selected + 1); evt.preventDefault(); return; }
    if (evt.key === "k" || evt.key === "ArrowUp") { selectIndex(state.selected - 1); evt.preventDefault(); return; }
    if (evt.key === "Enter") { openSelected(); evt.preventDefault(); return; }
    if (evt.key === "n") { jumpToNextUnresolved(); evt.preventDefault(); return; }

    if (state.openIndex < 0) return;
    var openForm2 = document.querySelector("#meeting-detail form[data-role='vote-form']");

    if (evt.key === "a") {
      var item = state.items[state.openIndex];
      if (item && item.type === "standard") {
        var amendBtn = document.querySelector("#meeting-detail button");
        var btns = document.querySelectorAll("#meeting-detail button");
        btns.forEach(function (b) { if (/^Amend this finding/.test(b.textContent)) b.click(); });
        evt.preventDefault();
      }
      return;
    }

    if (openForm2 && ["c", "f", "t", "w"].indexOf(evt.key) !== -1) {
      var map = { c: "carried", f: "failed", t: "tabled", w: "withdrawn" };
      var radio = openForm2.querySelector('input[name="outcome"][value="' + map[evt.key] + '"]');
      if (radio) { radio.checked = true; evt.preventDefault(); }
    }
  });

  $("help-close").addEventListener("click", function () { toggleHelp(false); });
  $("btn-refresh").addEventListener("click", function () { loadAgenda(true); });

  // ------------------------------------------------------------------- //
  // Boot
  // ------------------------------------------------------------------- //

  prepareThenLoad();
})();
