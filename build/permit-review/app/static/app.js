// Newcastle Permit Review — worksheet page behavior.
// Vanilla JS only, no npm, no build step (CONTRACT.md §8).

(function () {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  // ---- Copy as Markdown -------------------------------------------------
  var copyBtn = $("copy-md-btn");
  if (copyBtn) {
    copyBtn.addEventListener("click", function () {
      var src = $("worksheet-markdown-source");
      var text = src ? src.value : "";
      if (!text) {
        return;
      }
      var done = function () {
        var original = copyBtn.textContent;
        copyBtn.textContent = "Copied!";
        setTimeout(function () {
          copyBtn.textContent = original;
        }, 1500);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () {
          fallbackCopy(text, done);
        });
      } else {
        fallbackCopy(text, done);
      }
    });
  }

  function fallbackCopy(text, done) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
      done();
    } catch (e) {
      /* clipboard unavailable; user can select the hidden textarea manually */
    }
    document.body.removeChild(ta);
  }

  // ---- Generate PDF panel ------------------------------------------------
  var toggleBtn = $("toggle-render-btn");
  var renderForm = $("render-form");
  if (toggleBtn && renderForm) {
    toggleBtn.addEventListener("click", function () {
      renderForm.hidden = !renderForm.hidden;
    });
  }

  var submitBtn = $("render-submit-btn");
  if (submitBtn) {
    submitBtn.addEventListener("click", function () {
      var dataEl = $("worksheet-data");
      var district = dataEl ? dataEl.getAttribute("data-district") : "";
      var use = dataEl ? dataEl.getAttribute("data-use") : "";
      var lotsRaw = ($("lots").value || "").trim();
      var lots = lotsRaw
        ? lotsRaw.split(",").map(function (s) {
            return { label: s.trim() };
          }).filter(function (l) {
            return l.label.length > 0;
          })
        : [];

      var body = {
        ruleset_key: "adopted",
        district_key: district,
        use_keys: use ? [use] : [],
        case_label: $("case-label").value || "",
        meeting_month: $("meeting-month").value || null,
        lots: lots,
        notes: $("notes").value || "",
        scratch: $("scratch").checked,
      };

      var resultEl = $("render-result");
      resultEl.className = "render-result";
      resultEl.textContent = "Rendering…";
      submitBtn.disabled = true;

      fetch("/api/worksheet/render", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
        .then(function (resp) {
          return resp.json().then(function (json) {
            return { status: resp.status, json: json };
          });
        })
        .then(function (result) {
          submitBtn.disabled = false;
          if (result.json.ok) {
            var d = result.json.data;
            var lines = [
              "Rendered: " + d.path,
              d.bytes + " bytes · sha256 " + d.sha256.slice(0, 12) + "…",
              "Meeting date: " + d.meeting_date + " · Draft due: " + d.draft_due,
            ];
            if (d.unresolved && d.unresolved.length) {
              lines.push(d.unresolved.length + " unresolved item(s) — see the PDF for detail.");
            }
            resultEl.className = "render-result success";
            resultEl.textContent = lines.join("\n");
          } else {
            resultEl.className = "render-result error";
            var msg = result.json.message || result.json.error || "Render failed.";
            if (result.json.details) {
              msg += "\n" + JSON.stringify(result.json.details, null, 2);
            }
            resultEl.textContent = msg;
          }
        })
        .catch(function (e) {
          submitBtn.disabled = false;
          resultEl.className = "render-result error";
          resultEl.textContent = "Request failed: " + e;
        });
    });
  }
})();
