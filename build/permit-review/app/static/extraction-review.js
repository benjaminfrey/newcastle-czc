// Newcastle Permit Review — extraction review screen behavior.
// Vanilla JS only, no npm, no build step (CONTRACT.md §8).
//
// Every action here (confirm / override / not-applicable) is a POST to
// app/routes/extraction.py, which calls into app/extraction.py -- this file
// does no field-review logic of its own, it only collects the operator's
// input and reloads the page on success so the freshly-recorded decision
// (and its events-row audit trail) renders from the server, not a locally
// guessed re-render.

(function () {
  "use strict";

  function $all(selector, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(selector));
  }

  function postJSON(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function (resp) {
      return resp.json().then(function (json) {
        return { status: resp.status, json: json };
      });
    });
  }

  function showResult(el, result, successText) {
    if (!el) {
      return result.json.ok;
    }
    if (result.json.ok) {
      el.className = "render-result field-result success";
      el.textContent = successText || "Saved.";
    } else {
      el.className = "render-result field-result error";
      var msg = result.json.message || result.json.error || "Request failed.";
      if (result.json.details) {
        msg += " " + JSON.stringify(result.json.details);
      }
      el.textContent = msg;
    }
    return result.json.ok;
  }

  // subject_key round-trips through a data-attribute, where "no subject"
  // has to be the empty string rather than a missing attribute -- convert
  // back to a real null before it goes in a JSON body, matching how
  // app/extraction.py's `subject_key IS ?` queries expect NULL, not "".
  function nullIfEmpty(v) {
    return v === "" || v === null || v === undefined ? null : v;
  }

  function parseOverrideValue(raw) {
    var trimmed = (raw || "").trim();
    if (trimmed === "") {
      return { value_num: null, value_text: null };
    }
    if (/^-?\d+(\.\d+)?$/.test(trimmed)) {
      return { value_num: Number(trimmed), value_text: null };
    }
    return { value_num: null, value_text: trimmed };
  }

  var list = document.querySelector(".field-card-list");
  if (!list) {
    return;
  }
  var caseId = list.getAttribute("data-case-id");

  $all(".field-card", list).forEach(function (card) {
    var fieldDefId = card.getAttribute("data-field-def-id");
    var subjectKey = nullIfEmpty(card.getAttribute("data-subject-key"));
    var resultEl = card.querySelector(".field-result");
    var whyInput = card.querySelector(".field-confirm-why");

    // ---- Confirm one candidate ------------------------------------------
    $all(".confirm-candidate-btn", card).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var candidateEl = btn.closest(".candidate");
        var candidateId = candidateEl ? candidateEl.getAttribute("data-candidate-id") : null;
        var why = whyInput ? whyInput.value : "";
        if (!why || !why.trim()) {
          showResult(resultEl, { json: { ok: false, error: "validation_failed", message: "Enter why before confirming a value." } });
          if (whyInput) {
            whyInput.focus();
          }
          return;
        }
        resultEl.className = "render-result field-result";
        resultEl.textContent = "Confirming…";
        postJSON("/api/cases/" + encodeURIComponent(caseId) + "/fields/confirm", {
          field_def_id: fieldDefId,
          subject_key: subjectKey,
          candidate_id: candidateId,
          why: why,
        }).then(function (result) {
          var ok = showResult(resultEl, result, "Confirmed.");
          if (ok) {
            window.location.reload();
          }
        }).catch(function (e) {
          resultEl.className = "render-result field-result error";
          resultEl.textContent = "Request failed: " + e;
        });
      });
    });

    // ---- Override ----------------------------------------------------------
    var overrideForm = card.querySelector(".override-form");
    if (overrideForm) {
      overrideForm.addEventListener("submit", function (evt) {
        evt.preventDefault();
        var rawValue = overrideForm.querySelector("input[name=value]").value;
        var unit = overrideForm.querySelector("input[name=unit]").value;
        var reason = overrideForm.querySelector("input[name=reason]").value;
        var parsed = parseOverrideValue(rawValue);

        resultEl.className = "render-result field-result";
        resultEl.textContent = "Saving override…";
        postJSON("/api/cases/" + encodeURIComponent(caseId) + "/fields/override", {
          field_def_id: fieldDefId,
          subject_key: subjectKey,
          value_num: parsed.value_num,
          value_text: parsed.value_text,
          unit: unit || null,
          reason: reason,
        }).then(function (result) {
          var ok = showResult(resultEl, result, "Override recorded.");
          if (ok) {
            window.location.reload();
          }
        }).catch(function (e) {
          resultEl.className = "render-result field-result error";
          resultEl.textContent = "Request failed: " + e;
        });
      });
    }

    // ---- Not applicable ------------------------------------------------
    var naForm = card.querySelector(".not-applicable-form");
    if (naForm) {
      naForm.addEventListener("submit", function (evt) {
        evt.preventDefault();
        var why = naForm.querySelector("input[name=why]").value;

        resultEl.className = "render-result field-result";
        resultEl.textContent = "Saving…";
        postJSON("/api/cases/" + encodeURIComponent(caseId) + "/fields/not-applicable", {
          field_def_id: fieldDefId,
          subject_key: subjectKey,
          why: why,
        }).then(function (result) {
          var ok = showResult(resultEl, result, "Marked not applicable.");
          if (ok) {
            window.location.reload();
          }
        }).catch(function (e) {
          resultEl.className = "render-result field-result error";
          resultEl.textContent = "Request failed: " + e;
        });
      });
    }
  });
})();
