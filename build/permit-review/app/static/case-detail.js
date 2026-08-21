// Newcastle Permit Review — case detail page behavior.
// Vanilla JS only, no npm, no build step (CONTRACT.md §8).

(function () {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  function postJSON(url, method, body) {
    return fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function (resp) {
      return resp.json().then(function (json) {
        return { status: resp.status, json: json };
      });
    });
  }

  function showResult(el, result, successText) {
    if (result.json.ok) {
      el.className = "render-result success";
      el.textContent = successText || "Done.";
    } else {
      el.className = "render-result error";
      var msg = result.json.message || result.json.error || "Request failed.";
      if (result.json.details) {
        msg += " " + JSON.stringify(result.json.details);
      }
      el.textContent = msg;
    }
    return result.json.ok;
  }

  // ---- Status transition -------------------------------------------------
  var statusForm = $("status-form");
  if (statusForm) {
    statusForm.addEventListener("submit", function (evt) {
      evt.preventDefault();
      var caseId = statusForm.getAttribute("data-case-id");
      var toStatus = $("to-status").value;
      var why = $("status-why").value;
      var resultEl = $("status-result");
      resultEl.className = "render-result";
      resultEl.textContent = "Updating…";

      postJSON("/api/cases/" + encodeURIComponent(caseId) + "/status", "POST", {
        to_status: toStatus,
        why: why,
      }).then(function (result) {
        var ok = showResult(resultEl, result, "Status updated.");
        if (ok) {
          window.location.reload();
        }
      }).catch(function (e) {
        resultEl.className = "render-result error";
        resultEl.textContent = "Request failed: " + e;
      });
    });
  }

  // ---- Record a key date --------------------------------------------------
  var addDateForm = $("add-date-form");

  // F5 repair path: a "Correct this date" button on a flagged (invalid
  // occurred_on) row in the Key Dates table pre-fills the same add-date
  // form with that row's kind and a hidden supersedes_id, so submitting it
  // records a NEW, valid entry and marks the old row superseded (via
  // app.cases.record_dates' existing supersedes_id mechanism) rather than
  // editing or deleting the bad row -- case_milestones stays append-only.
  var supersedesInput = $("add-date-supersedes-id");
  var correctingNote = $("add-date-correcting-note");
  var cancelCorrectBtn = $("add-date-cancel-correct");
  // N3: the reason field is only meaningful (and only required by
  // app.cases.record_dates) once a supersedes_id is set -- kept hidden and
  // un-required the rest of the time so an ordinary new-date entry never has
  // to think about it.
  var reasonField = $("add-date-reason-field");
  var reasonSelect = $("add-date-supersede-reason");

  function setCorrecting(milestoneId, kind) {
    if (!addDateForm || !supersedesInput) {
      return;
    }
    supersedesInput.value = milestoneId || "";
    if (kind) {
      var kindSelect = addDateForm.querySelector("select[name=kind]");
      if (kindSelect) {
        kindSelect.value = kind;
      }
    }
    if (correctingNote) {
      correctingNote.hidden = !milestoneId;
    }
    if (reasonField) {
      reasonField.hidden = !milestoneId;
    }
    if (reasonSelect) {
      reasonSelect.required = !!milestoneId;
      if (!milestoneId) {
        reasonSelect.value = "correction";
      }
    }
    if (milestoneId) {
      addDateForm.scrollIntoView({ behavior: "smooth", block: "center" });
      var occurredInput = addDateForm.querySelector("input[name=occurred_on]");
      if (occurredInput) {
        occurredInput.focus();
      }
    }
  }

  document.querySelectorAll(".correct-date-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      setCorrecting(btn.getAttribute("data-milestone-id"), btn.getAttribute("data-kind"));
    });
  });

  if (cancelCorrectBtn) {
    cancelCorrectBtn.addEventListener("click", function () {
      setCorrecting(null, null);
    });
  }

  if (addDateForm) {
    addDateForm.addEventListener("submit", function (evt) {
      evt.preventDefault();
      var caseId = addDateForm.getAttribute("data-case-id");
      var fd = new FormData(addDateForm);
      var entry = {
        kind: fd.get("kind"),
        occurred_on: fd.get("occurred_on"),
      };
      var note = fd.get("note");
      if (note) {
        entry.note = note;
      }
      var supersedesId = fd.get("supersedes_id");
      if (supersedesId) {
        entry.supersedes_id = supersedesId;
        // N3: required server-side whenever supersedes_id is given --
        // app.cases.record_dates raises ValidationError without it rather
        // than inferring "reschedule" vs "correction" from the dates alone.
        entry.supersede_reason = fd.get("supersede_reason");
      }
      var resultEl = $("add-date-result");
      resultEl.className = "render-result";
      resultEl.textContent = "Recording…";

      postJSON("/api/cases/" + encodeURIComponent(caseId) + "/dates", "PATCH", {
        dates: [entry],
        why: fd.get("why"),
      }).then(function (result) {
        var ok = showResult(resultEl, result, "Recorded.");
        if (ok) {
          window.location.reload();
        }
      }).catch(function (e) {
        resultEl.className = "render-result error";
        resultEl.textContent = "Request failed: " + e;
      });
    });
  }

  // ---- Finding 3: record a §6.e.1 clock extension --------------------------
  var addExtensionForm = $("add-extension-form");
  if (addExtensionForm) {
    addExtensionForm.addEventListener("submit", function (evt) {
      evt.preventDefault();
      var caseId = addExtensionForm.getAttribute("data-case-id");
      var fd = new FormData(addExtensionForm);
      var entry = {
        kind: "extension_agreed",
        target_clock_key: fd.get("target_clock_key"),
        extension_days: parseInt(fd.get("extension_days"), 10),
        occurred_on: fd.get("occurred_on"),
        written_agreement_ref: fd.get("written_agreement_ref"),
      };
      var note = fd.get("note");
      if (note) {
        entry.note = note;
      }
      var resultEl = $("add-extension-result");
      resultEl.className = "render-result";
      resultEl.textContent = "Recording…";

      postJSON("/api/cases/" + encodeURIComponent(caseId) + "/dates", "PATCH", {
        dates: [entry],
        why: fd.get("why"),
      }).then(function (result) {
        var ok = showResult(resultEl, result, "Extension recorded.");
        if (ok) {
          window.location.reload();
        }
      }).catch(function (e) {
        resultEl.className = "render-result error";
        resultEl.textContent = "Request failed: " + e;
      });
    });
  }

  // ---- Finding 3: mark a clock waived / not applicable ----------------------
  var addOverrideForm = $("add-override-form");
  if (addOverrideForm) {
    addOverrideForm.addEventListener("submit", function (evt) {
      evt.preventDefault();
      var caseId = addOverrideForm.getAttribute("data-case-id");
      var fd = new FormData(addOverrideForm);
      var entry = {
        kind: fd.get("kind"),
        target_clock_key: fd.get("target_clock_key"),
        occurred_on: fd.get("occurred_on"),
        note: fd.get("note"),
      };
      var resultEl = $("add-override-result");
      resultEl.className = "render-result";
      resultEl.textContent = "Recording…";

      postJSON("/api/cases/" + encodeURIComponent(caseId) + "/dates", "PATCH", {
        dates: [entry],
        why: fd.get("why"),
      }).then(function (result) {
        var ok = showResult(resultEl, result, "Recorded.");
        if (ok) {
          window.location.reload();
        }
      }).catch(function (e) {
        resultEl.className = "render-result error";
        resultEl.textContent = "Request failed: " + e;
      });
    });
  }

  // ---- Upload dropzone -----------------------------------------------------
  var dropzone = $("upload-dropzone");
  var fileInput = $("upload-file-input");
  var fileNameEl = $("upload-file-name");
  var uploadForm = $("upload-form");
  var submitBtn = $("upload-submit-btn");
  var progressTrack = $("upload-progress-track");
  var progressBar = $("upload-progress-bar");
  var statusEl = $("upload-status");

  var selectedFile = null;

  function setSelectedFile(file) {
    selectedFile = file || null;
    if (fileNameEl) {
      fileNameEl.textContent = selectedFile ? "Selected: " + selectedFile.name : "";
    }
    if (submitBtn) {
      submitBtn.disabled = !selectedFile;
    }
  }

  if (dropzone && fileInput) {
    dropzone.addEventListener("click", function () {
      fileInput.click();
    });
    dropzone.addEventListener("keydown", function (evt) {
      if (evt.key === "Enter" || evt.key === " ") {
        evt.preventDefault();
        fileInput.click();
      }
    });
    fileInput.addEventListener("change", function () {
      setSelectedFile(fileInput.files && fileInput.files[0]);
    });
    ["dragenter", "dragover"].forEach(function (evtName) {
      dropzone.addEventListener(evtName, function (evt) {
        evt.preventDefault();
        dropzone.classList.add("dragover");
      });
    });
    ["dragleave", "drop"].forEach(function (evtName) {
      dropzone.addEventListener(evtName, function (evt) {
        evt.preventDefault();
        dropzone.classList.remove("dragover");
      });
    });
    dropzone.addEventListener("drop", function (evt) {
      var files = evt.dataTransfer && evt.dataTransfer.files;
      if (files && files.length) {
        setSelectedFile(files[0]);
      }
    });
  }

  if (uploadForm) {
    uploadForm.addEventListener("submit", function (evt) {
      evt.preventDefault();
      if (!selectedFile) {
        return;
      }
      var caseId = uploadForm.getAttribute("data-case-id");
      var fd = new FormData(uploadForm);
      fd.append("file", selectedFile);

      statusEl.className = "upload-status";
      statusEl.textContent = "Uploading…";
      if (progressTrack) {
        progressTrack.hidden = false;
      }
      if (progressBar) {
        progressBar.style.width = "0%";
      }
      submitBtn.disabled = true;

      var xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/cases/" + encodeURIComponent(caseId) + "/documents");
      xhr.upload.addEventListener("progress", function (evt) {
        if (evt.lengthComputable && progressBar) {
          var pct = Math.round((evt.loaded / evt.total) * 100);
          progressBar.style.width = pct + "%";
        }
      });
      xhr.onload = function () {
        submitBtn.disabled = false;
        var json;
        try {
          json = JSON.parse(xhr.responseText);
        } catch (e) {
          json = { ok: false, message: "Could not parse server response." };
        }
        if (json.ok) {
          var census = json.data.tier_census || {};
          var parts = [];
          ["A", "B", "C", "D"].forEach(function (t) {
            if (census[t]) {
              parts.push(t + ": " + census[t]);
            }
          });
          statusEl.className = "upload-status success";
          statusEl.textContent = "Uploaded " + json.data.pages.length + " page(s). Tier census — "
            + (parts.length ? parts.join(", ") : "no pages") + ".";
          setSelectedFile(null);
          if (fileInput) {
            fileInput.value = "";
          }
          setTimeout(function () {
            window.location.reload();
          }, 1200);
        } else {
          statusEl.className = "upload-status error";
          var msg = json.message || json.error || "Upload failed.";
          if (json.details) {
            msg += " " + JSON.stringify(json.details);
          }
          statusEl.textContent = msg;
        }
      };
      xhr.onerror = function () {
        submitBtn.disabled = false;
        statusEl.className = "upload-status error";
        statusEl.textContent = "Upload request failed (network error).";
      };
      xhr.send(fd);
    });
  }
})();
