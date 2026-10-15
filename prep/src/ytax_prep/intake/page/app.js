/*
 * SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
 * Copyright (c) 2026 TRIPLE J AI LLC
 * Contains original software from the ytax project.
 * See the release-root LICENSING.md for scope and separate licensing options.
 */

// yTax intake page — no framework, nothing fetched from anywhere but this computer.
(function () {
  "use strict";
  var token = new URLSearchParams(location.search).get("t") || "";
  var aiStartedAt = 0;      // when THIS page saw the check start, for the elapsed clock
  var el = function (id) { return document.getElementById(id); };

  // A wait says what it is waiting on, moves, and counts its seconds, so nobody is
  // left looking at a page that seems to do nothing. Shown after a short moment, so a quick answer
  // does not flash.
  // A running model check is the other thing this bar shows (decided 2026-09-22: the model
  // reading the forms should wait the way computing the return waits). It is kept apart from the
  // stack, which pops its last entry when any request answers.
  var working = [], ticker = null, modelJob = null;

  function paintBusy() {
    var box = el("busy");
    if (!box) { return; }
    var job = working.length ? working[working.length - 1] : modelJob;
    if (!job) { box.hidden = true; clearInterval(ticker); ticker = null; return; }
    var secs = Math.floor((Date.now() - job.started) / 1000);
    if (secs < 1 && box.hidden && job !== modelJob && !job.now) { return; }
    box.hidden = false;
    el("busy-what").textContent = job.label + "…";
    el("busy-time").textContent = elapsed(secs);
    el("busy-stop").hidden = job !== modelJob;         // only the model's check can be stopped
    var bar = el("busy-bar");
    if (job.total) { bar.max = job.total; bar.value = job.done; } else { bar.removeAttribute("value"); }
  }

  function tick() {
    if (!ticker) { ticker = setInterval(paintBusy, 500); }
    paintBusy();
  }

  // `now`: shown at once rather than after a second — reading documents is the wait a person is
  // looking at, and each read finishing inside the second left the bar never shown.
  function busy(delta, label, now) {
    if (delta > 0) {
      working.push({label: label || "Working", started: Date.now(), now: !!now});
    } else {
      working.pop();
    }
    tick();
  }

  function api(method, path, body, headers, label, now) {
    var h = Object.assign({"X-Intake-Token": token}, headers || {});
    busy(1, label, now);
    return fetch(path, {method: method, headers: h, body: body}).then(function (r) {
      return r.json().then(function (data) {
        busy(-1);
        if (!r.ok) {
        var problem = new Error(data.error || data.unavailable || "Something went wrong.");
        if (data.duplicate) { problem.duplicate = data.duplicate; problem.message = data.duplicate.words; }
        throw problem;
      }
        return data;
      });
    }).catch(function (e) { busy(-1); throw e; });
  }

  function text(tag, content, cls) {
    var n = document.createElement(tag);
    n.textContent = content == null ? "" : String(content);
    if (cls) { n.className = cls; }
    return n;
  }

  function showError(e) { el("error").textContent = e ? e.message : ""; }

  // where this works. Asked BEFORE anything is read or written, and shown from then on.
  var folderConfirmed = false;

  function renderFolder(state) {
    var box = el("turn");
    box.textContent = "";
    box.appendChild(text("p", "Where should this work? Your documents are read from this folder's "
                              + "input, and the filled forms are written to its output.", "ask"));
    box.appendChild(text("p", "If you want your name, address and taxpayer ID printed on the forms, "
                              + "put a file named case.identity.ini in that input folder. It is read "
                              + "only when the forms are filled, and nothing from it is computed or "
                              + "stored with your figures.", "why"));
    var field = document.createElement("input");
    field.type = "text";
    field.id = "folder";
    field.value = state.folder || "";
    field.size = 60;
    field.autocomplete = "off";   // the browser's own memory of an old path filled this in
    field.setAttribute("aria-label", "Working folder");
    var use = text("button", "Use this folder");
    use.type = "button";
    use.onclick = function () {
      showError(null);
      api("POST", "/api/folder", JSON.stringify({path: field.value}), {"Content-Type": "application/json"}, "Opening the folder")
        .then(function () { folderConfirmed = true; refresh(); }).catch(showError);
    };
    var browse = text("button", "Browse folders");
    browse.type = "button";
    var tree = document.createElement("div");
    tree.className = "tree";
    tree.hidden = true;
    function showTree(path) {
      showError(null);
      api("GET", "/api/browse?path=" + encodeURIComponent(path || "")).then(function (d) {
        tree.textContent = "";
        tree.hidden = false;
        var here = text("p", d.path + (d.windows ? "  (on Windows: " + d.windows + ")" : ""), "why");
        tree.appendChild(here);
        var list = document.createElement("ul");
        list.className = "folders";
        if (d.parent) {
          var up = text("li", "");
          var upLink = text("button", "↑ up to " + d.parent);
          upLink.type = "button";
          upLink.onclick = function () { showTree(d.parent); };
          up.appendChild(upLink);
          list.appendChild(up);
        }
        d.folders.forEach(function (name) {
          var li = text("li", "");
          var link = text("button", name + "/");
          link.type = "button";
          link.onclick = function () { showTree(d.path.replace(/\/$/, "") + "/" + name); };
          li.appendChild(link);
          list.appendChild(li);
        });
        tree.appendChild(list);
        var pick = text("button", "Use " + d.path);
        pick.type = "button";
        pick.onclick = function () { field.value = d.path; use.onclick(); };
        tree.appendChild(pick);
      }).catch(showError);
    }
    // The Windows folder picker, opened by the program on this computer. Where none can be opened,
    // the page's own folder list is shown instead.
    browse.onclick = function () {
      showError(null);
      api("POST", "/api/folder/pick", JSON.stringify({start: field.value}), {"Content-Type": "application/json"},
          "Waiting for you to choose a folder in the window that opened")
        .then(function (d) {
          if (d.path) { field.value = d.path; use.onclick(); }
        })
        .catch(function () { showTree(field.value); });
    };
    box.appendChild(field);
    box.appendChild(use);
    box.appendChild(browse);
    box.appendChild(tree);
    el("tray").hidden = true;
  }

  function renderReads(s) {
    var reads = s.reads || [];
    if (!reads.length) { return; }
    var box = el("reads");
    box.textContent = "";
    box.appendChild(text("p", "This page reads these forms from a document: " + reads.join(", ") + ".", "why"));
    box.appendChild(text("p", "Why only these: a document is read where the pinned dictionary has a box register for the form and this return carries the figures. " +
      "Typed in, not read from a document: " + (s.typed_not_read || []).join("; ") + ".", "why"));
    box.appendChild(text("p", "Not carried by this return at all, so a document of this kind is named and its figures are not used: " +
      (s.not_carried || []).join("; ") + ".", "why"));
  }

  function renderIdentity(identity) {
    if (!identity) { return; }
    var list = el("identity-fields");
    list.textContent = "";
    if (identity.problem) { el("identity-note").textContent = identity.problem; }
    var inputs = {};
    (identity.fields || []).forEach(function (f) {
      var row = document.createElement("li");
      var label = document.createElement("label");
      var input = document.createElement("input");
      input.type = "text";
      input.size = 18;
      input.autocomplete = "off";
      input.value = f.value || "";
      label.appendChild(text("span", f.label + " "));
      label.appendChild(input);
      row.appendChild(label);
      list.appendChild(row);
      inputs[f.term] = input;
    });
    el("identity-save").onclick = function () {
      showError(null);
      var values = {};
      Object.keys(inputs).forEach(function (term) { values[term] = inputs[term].value; });
      api("POST", "/api/identity", JSON.stringify({values: values}), {"Content-Type": "application/json"})
        .then(function (d) {
          var n = (d.identity.fields || []).filter(function (f) { return f.value; }).length;
          el("identity-note").textContent = n ? "Kept on this computer, in " + d.identity.file + ". The forms will carry them." :
            "Nothing kept; the forms will leave those boxes blank.";
        }).catch(showError);
    };
  }

  // The notation strip at the top of Form 1040, in the form's own words. Nothing
  // here is computed; the answers stay in the working folder and print on the form.
  var NOTATIONS = [
    {key: "section_9100_relief", words: "Filed pursuant to section 301.9100-2"},
    {key: "combat_zone", words: "Combat zone"},
    {key: "deceased", words: "Deceased", date: "Date of death"},
    {key: "other", words: "Other (specify)", entries: 3}
  ];

  function renderNotations(state) {
    var list = el("notation-fields");
    if (!list) { return; }
    var kept = (state && state.values) || {};
    list.textContent = "";
    if (state && state.problem) { el("notations-note").textContent = state.problem; }
    var ticks = {}, date = null, entries = [];
    NOTATIONS.forEach(function (n) {
      var row = document.createElement("li");
      var label = document.createElement("label");
      var input = document.createElement("input");
      input.type = "checkbox";
      input.checked = !!kept[n.key];
      label.appendChild(input);
      label.appendChild(text("span", " " + n.words));
      row.appendChild(label);
      ticks[n.key] = input;
      if (n.date) {
        var dateLabel = document.createElement("label");
        date = document.createElement("input");
        date.type = "date";
        date.value = kept.date_of_death || "";
        dateLabel.appendChild(text("span", " " + n.date + " "));
        dateLabel.appendChild(date);
        row.appendChild(dateLabel);
      }
      for (var i = 0; i < (n.entries || 0); i++) {
        var entryLabel = document.createElement("label");
        var entry = document.createElement("input");
        entry.type = "text";
        entry.size = 18;
        entry.value = (kept.other_entries || [])[i] || "";
        entryLabel.appendChild(text("span", " " + n.words + " " + (i + 1) + " "));
        entryLabel.appendChild(entry);
        row.appendChild(entryLabel);
        entries.push(entry);
      }
      list.appendChild(row);
    });
    el("notations-save").onclick = function () {
      showError(null);
      var values = {other_entries: entries.map(function (e) { return e.value; })};
      Object.keys(ticks).forEach(function (k) { values[k] = ticks[k].checked; });
      if (date) { values.date_of_death = date.value; }
      api("POST", "/api/notations", JSON.stringify({values: values}), {"Content-Type": "application/json"},
          "Keeping the notations")
        .then(function (d) {
          var on = Object.keys(d.notations.values).filter(function (k) { return d.notations.values[k] === true; });
          el("notations-note").textContent = on.length
            ? "Kept on this computer, in " + d.notations.file + "; the form will carry them."
            : "Nothing is ticked, so the form's notation strip stays empty.";
        }).catch(showError);
    };
  }

  function renderDocuments(docs) {
    var list = el("documents");
    list.textContent = "";
    (docs || []).forEach(function (d) {
      var line = d.name + " — " + (d.form || "not recognised") + ": " +
        (d.unconsumed ? d.unconsumed
         : d.form === "workbook" ? d.read + " answer(s) taken from the workbook"
         : d.read + " box(es) read");
      var item = text("li", line);
      (d.identity_notes || []).forEach(function (said) {
        item.appendChild(text("div", said, "identity-note"));
      });
      if (d.not_read && d.not_read.length) {
        // A box the paper shows a figure in that no fact receives: the person is told which, by
        // box number and caption, in the standard's own words; the figure stays on the paper.
        // Decided 2026-09-26: the boxes that can change a line on the return are
        // named apart from the ones stored only. `not_read_lines` holds the first kind (a box the
        // dictionary does not model yet is there too — never called "stored only").
        // A document read before this split (a saved return from an earlier sitting) has no
        // `not_read_lines` at all: it keeps the single line, rather than calling every box "stored only".
        var lines = d.not_read_lines;
        if (!lines) {
          item.appendChild(text("div", "Not read from this form: " + d.not_read.join("; ") + "."));
        } else {
          var has = function (n) { return lines.hasOwnProperty(n); };
          var changes = d.not_read.filter(function (n) { return has(n) && lines[n].length; });
          var unknown = d.not_read.filter(function (n) { return has(n) && !lines[n].length; });
          var stored = d.not_read.filter(function (n) { return !has(n); });
          if (changes.length) {
            item.appendChild(text("div", "Not read from this form, and it can change a line on your " +
              "return: " + changes.join("; ") + ".", "not-read-changes"));
          }
          if (unknown.length) {
            item.appendChild(text("div", "Not read from this form, and not in the tax rules this " +
              "version carries yet (whether it changes a line is not known): " + unknown.join("; ") +
              ".", "not-read-changes"));
          }
          if (stored.length) {
            item.appendChild(text("div", "Not read from this form, stored only (no line on this " +
              "return uses it): " + stored.join("; ") + "."));
          }
        }
      }
      list.appendChild(item);
    });
  }

  // A check by a local AI model — asked, never assumed; what the page says first is
  // what Ollama and the model report about themselves. The model changes nothing: its reading is
  // listed beside the page's for the person to compare.
  function quiet(path) {
    return fetch(path, {headers: {"X-Intake-Token": token}}).then(function (r) { return r.json(); });
  }

  var PART_WORDS = {documents: "reading the documents again", read_back: "reading every filled entry back",
                    empty_boxes: "looking for boxes left empty", trace: "tracing each document figure to the forms"};
  // information, shaded; anything else that is not agreement is highlighted
  var NEUTRAL = {"carried to this line": true, "counted in this line with other documents": true,
                 "the same amount appears here": true, "does not print on the filled forms": true,
                 "that line was not found in the read-back": true,
                 "the model reads this as empty; look at it": true};

  function minutes(secs) {
    if (secs == null) { return ""; }
    return secs < 90 ? "about " + secs + " s left" : "about " + Math.round(secs / 60) + " min left";
  }

  function elapsed(secs) {
    return secs < 90 ? secs + " s" : Math.round(secs / 60) + " min";
  }

  function renderLog(log) {
    var area = el("ai-log");
    if (area == null || log == null) { return; }
    var atEnd = area.scrollTop + area.clientHeight >= area.scrollHeight - 4;
    area.value = log;
    if (atEnd) { area.scrollTop = area.scrollHeight; }
  }

  function renderAiRows(check) {
    var status = el("ai-status"), box = el("ai-rows");
    box.textContent = "";
    if (!check || check.status !== "running") { modelJob = null; tick(); }
    if (!check || check.status === "idle") { status.textContent = ""; aiStartedAt = 0; return; }
    if (check.status !== "running") { aiStartedAt = 0; }
    if (check.log != null) { renderLog(check.log); }
    var what = check.what === "filled" ? "the filled forms" : "the documents";
    var parts = check.parts || [];
    if (check.status === "running") {
      var step = parts.indexOf(check.part) + 1;
      // A clock that moves. These models run on the processor and one page can take minutes, so
      // between two replies nothing on this screen changed and the page read as stopped (seen
      // 2026-09-22). The elapsed time is the page's own, not the server's.
      if (!aiStartedAt) { aiStartedAt = Date.now(); }
      // the same bar, words and clock as computing the return, at the top of the page
      modelJob = {started: aiStartedAt, total: check.total, done: check.done,
                  label: "The model is " + (PART_WORDS[check.part] || "starting") +
                    (parts.length > 1 && step ? " (step " + step + " of " + parts.length + ")" : "") +
                    (check.total ? ": " + check.done + " of " + check.total + " done" : "") +
                    (check.now ? ", now " + check.now : "") +
                    (check.eta_seconds != null ? ", " + minutes(check.eta_seconds) : "")};
      tick();
      status.textContent = "The model is checking " + what + "; its progress is in the bar at the top of the page. " +
        "Where the model runs mostly on the processor, one page can take minutes; the model log below names each document as it is reached and shows each reply as it comes.";
      poll();
    } else if (check.status === "error" || check.status === "stopped") {
      status.textContent = check.problem || "The check stopped.";
    }
    var rows = check.rows || [];
    if (!rows.length) {
      // a finished check that compared nothing said nothing, and the running words stayed on
      // screen — which reads as a page that stopped working (seen 2026-09-22)
      if (check.status === "done") {
        status.textContent = "The model finished with " + what + " and had nothing to compare — "
          + "no box was read on both sides. The model log says what it was asked and what it said.";
      }
      return;
    }
    if (check.status === "done") {
      var differ = rows.filter(function (r) { return r.verdict !== "agrees" && !NEUTRAL[r.verdict]; }).length;
      status.textContent = "The model has finished with " + what + ". " + (differ ?
        differ + " row(s) are highlighted where its reading and this page's are not the same, or a box reads as empty." :
        "Its reading and this page's are the same wherever both have a value.");
    }
    var table = document.createElement("table");
    var head = table.createTHead().insertRow();
    ["Where", "Box", "This page", "The model", "Result"].forEach(function (h) { head.appendChild(text("th", h)); });
    var body = table.createTBody();
    rows.forEach(function (r) {
      var row = body.insertRow();
      row.className = r.verdict === "agrees" ? "agrees" : (NEUTRAL[r.verdict] ? "neutral" : "differs");
      [r.where, r.box, r.page, r.model, r.verdict].forEach(function (v) { row.appendChild(text("td", v)); });
    });
    box.appendChild(table);
  }

  function renderAi(a) {
    var section = el("ai"), body = el("ai-body");
    section.hidden = false;
    body.textContent = "";
    if (!a.offered) { body.appendChild(text("p", a.note, "why")); el("ai-log-box").hidden = true; renderAiRows(null); return; }
    el("ai-log-box").hidden = false;
    body.appendChild(text("p", "Have an AI model on this computer read your documents and the filled forms again, and list each box it reads differently?", "ask"));
    var facts = document.createElement("ul");
    (a.facts || []).forEach(function (f) { facts.appendChild(text("li", f, "why")); });
    body.appendChild(facts);
    var set = document.createElement("fieldset");
    set.appendChild(text("legend", "Your answer"));
    var choices = [{value: "no", words: "No"}].concat((a.models || []).map(function (m) {
      return {value: "yes", model: m.name, words: "Yes, with " + m.words};
    }));
    var radios = [];
    choices.forEach(function (c, i) {
      var label = document.createElement("label");
      var input = document.createElement("input");
      input.type = "radio";
      input.name = "ai-answer";
      input.checked = a.answer === "yes" ? c.model === a.model : i === 0;
      label.appendChild(input);
      label.appendChild(document.createTextNode(" " + c.words));
      set.appendChild(label);
      set.appendChild(document.createElement("br"));
      radios.push({input: input, choice: c});
    });
    body.appendChild(set);
    // The checks of the filled forms, each a choice
    var opts = document.createElement("fieldset");
    opts.appendChild(text("legend", "When the filled forms are checked"));
    var boxes = {};
    [["read_back", "Read every filled entry back and compare it with what was written"],
     ["empty_boxes", "Look over each page for boxes left empty that the form asks for"],
     ["trace", "Trace each amount from your documents to where it prints on the forms"],
     ["after_fill", "Start this check by itself each time the forms are filled"]].forEach(function (o) {
      var label = document.createElement("label");
      var input = document.createElement("input");
      input.type = "checkbox";
      input.checked = !!(a.options || {})[o[0]];
      label.appendChild(input);
      label.appendChild(document.createTextNode(" " + o[1]));
      opts.appendChild(label);
      opts.appendChild(document.createElement("br"));
      boxes[o[0]] = input;
    });
    body.appendChild(opts);
    var keep = text("button", "Keep these answers");
    keep.type = "button";
    keep.onclick = function () {
      showError(null);
      var picked = radios.filter(function (r) { return r.input.checked; })[0].choice;
      var options = {};
      Object.keys(boxes).forEach(function (k) { options[k] = boxes[k].checked; });
      api("POST", "/api/ai", JSON.stringify({answer: picked.value, model: picked.model, options: options}),
          {"Content-Type": "application/json"}, "Keeping your answers")
        .then(refreshAi).catch(showError);
    };
    body.appendChild(keep);
    if (a.answer === "yes") {
      // …and why a button is off. A dead control with no reason reads as a broken page: a
      // person pressed both of these on an empty folder and nothing happened at all, because
      // nothing happening is exactly what a disabled button does (2026-09-22).
      [["documents", "Check the figures read from the documents", !a.documents,
        "Add a tax document first — a model re-reads the pages of a form this version reads."],
       ["filled", "Check the filled forms", !a.filled,
        a.filled_earlier ? "The forms in the output folder were filled before this return last changed; fill them again first."
                         : "Fill the forms first — there is nothing written to read back yet."]].forEach(function (b) {
        var button = text("button", b[1]);
        button.type = "button";
        button.disabled = b[2] || (a.check && a.check.status === "running");
        button.onclick = function () {
          showError(null);
          api("POST", "/api/check", JSON.stringify({what: b[0]}), {"Content-Type": "application/json"}, "Starting the check")
            .then(renderAiRows).then(refreshAi).catch(showError);
        };
        body.appendChild(document.createTextNode(" "));
        body.appendChild(button);
        if (b[2]) { body.appendChild(text("p", b[3], "why")); }
      });
    } else if (a.answer === "no") {
      body.appendChild(text("p", "No model reads anything on this page.", "why"));
    }
    renderAiRows(a.check);
    quiet("/api/check").then(function (c) { renderLog(c.log); }).catch(function () {});
  }

  el("busy-stop").addEventListener("click", function () {
    showError(null);
    el("busy-stop").disabled = true;
    // honoured between pages: the page the model is reading now finishes first
    api("POST", "/api/check/stop", null, null, "Asking the model's check to stop after this page")
      .then(function () { el("ai-status").textContent = "Stopping after the page the model is reading now…"; })
      .catch(showError)
      .then(function () { el("busy-stop").disabled = false; });
  });

  el("ai-log-copy").addEventListener("click", function () {
    var area = el("ai-log"), note = el("ai-log-note");
    area.focus();
    area.select();
    var done = function () { note.textContent = "Copied."; };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(area.value).then(done, function () {
        note.textContent = document.execCommand("copy") ? "Copied." : "Selected; press Ctrl+C to copy.";
      });
    } else {
      note.textContent = document.execCommand("copy") ? "Copied." : "Selected; press Ctrl+C to copy.";
    }
  });

  var polling = false;
  function poll() {
    if (polling) { return; }
    polling = true;
    setTimeout(function () {
      polling = false;
      quiet("/api/check").then(function (c) {
        if (c.status === "running") { renderAiRows(c); } else { refreshAi(); }
      }).catch(showError);
    }, 3000);
  }

  function refreshAi() {
    return quiet("/api/ai").then(renderAi).catch(showError);
  }

  // An answer is sent once. The first compute takes seconds and the bar shows only after one, so
  // a second click sent the same answer again and came back "That question has already moved on"
  // (found by the browser cases on the bundle, 2026-09-22). The buttons wait with the page.
  function holdButtons(on) {
    Array.prototype.forEach.call(el("turn").querySelectorAll("button"), function (b) { b.disabled = on; });
  }

  function reply(turn, value) {
    showError(null);
    holdButtons(true);
    api("POST", "/api/reply", JSON.stringify({turn_id: turn.id, reply: value}),
        {"Content-Type": "application/json"}, "Working out what comes next").then(function (data) {
          renderTurn(data.turn, data.answers);
          showForms(data);
        }).catch(function (e) { holdButtons(false); showError(e); });
  }

  // A file in a folder, written with that folder's own separator: C:\…\output\f1040.pdf on
  // Windows, never C:\…\output/f1040.pdf.
  function inFolder(folder, name) {
    return folder + (folder.indexOf("\\") >= 0 && folder.indexOf("/") < 0 ? "\\" : "/") + name;
  }

  // The forms the output folder holds for THIS return, and — said, never listed as this return's —
  // any filled before the return last changed.
  var outputFolder = "";
  function showForms(d) {
    if (!d || d.filled === undefined) { return; }
    var list = el("filled");
    list.textContent = "";
    d.filled.forEach(function (n) { list.appendChild(text("li", inFolder(outputFolder, n))); });
    if (d.filled_earlier && d.filled_earlier.length) {
      list.appendChild(text("li", "The forms in " + outputFolder + " (" + d.filled_earlier.join(", ") +
        ") were filled before this return last changed, so they are not this return's. Fill the forms again.", "why"));
    }
    el("workbook").hidden = !d.filled.length;
  }

  // no screen is a dead end. A refusal (and the finished return) offers every answer this
  // person gave, in the words they were asked, so one can be changed and the questions continue.
  function answerControl(a) {
    // One control per answer, prefilled with what was said, so changing an answer
    // is picking or typing the new one right on the list.
    var input;
    if (a.type === "choice") {
      input = document.createElement("select");
      (a.choices || []).forEach(function (code, i) {
        var o = text("option", (a.labels && a.labels[i]) || code);
        o.value = code;
        if (String(a.value).toLowerCase() === String(code).toLowerCase()) { o.selected = true; }
        input.appendChild(o);
      });
    } else if (a.type === "date") {
      input = document.createElement("input");
      input.type = "date";                         // the day was not kept, so it starts empty
    } else {
      input = document.createElement("input");
      input.type = "text";
      input.size = a.type === "amount" ? 14 : 10;
      input.value = a.shown !== undefined ? a.shown : String(a.value);
    }
    input.setAttribute("aria-label", "Change: " + a.question);
    return input;
  }

  function answerList(box, answers, lead) {
    // Every question together, as a list: what was asked, the answer, and a control to change it.
    if (lead) { box.appendChild(text("p", lead, "why")); }
    var table = document.createElement("table");
    table.className = "answers";
    var head = table.createTHead().insertRow();
    ["What you were asked", "Your answer", "Change it to", ""].forEach(function (h) { head.appendChild(text("th", h)); });
    (answers || []).forEach(function (a) {
      var row = table.insertRow();
      row.setAttribute("data-path", a.path);
      row.appendChild(text("td", a.question));
      row.appendChild(text("td", a.shown !== undefined ? String(a.shown) : String(a.value)));
      var control = answerControl(a);
      row.insertCell().appendChild(control);
      var change = text("button", "Change");
      change.type = "button";
      change.onclick = function () {
        showError(null);
        // The changed answer stays where it was on the screen (seen 2026-09-22: changing a
        // value moved the field). The list is drawn again from the reply, in one step, and the page
        // scrolls by however far that row moved.
        var before = row.getBoundingClientRect().top;
        holdButtons(true);
        api("POST", "/api/change", JSON.stringify({path: a.path, reply: control.value}), {"Content-Type": "application/json"},
            "Changing the answer and working out what comes next")
          .then(function (data) {
            renderTurn(data.turn, data.answers);
            showForms(data);
            var rows = document.querySelectorAll("#turn tr[data-path]");
            for (var i = 0; i < rows.length; i++) {
              if (rows[i].getAttribute("data-path") === a.path) {
                window.scrollBy(0, rows[i].getBoundingClientRect().top - before);
                break;
              }
            }
          }).catch(function (e) { holdButtons(false); showError(e); });
      };
      row.insertCell().appendChild(change);
    });
    box.appendChild(table);
  }

  function changeAnswer(box, lead, answers) {
    var wrap = document.createElement("div");
    wrap.className = "again";
    if (answers) { answerList(wrap, answers, lead); }     // already in hand: drawn at once, nothing jumps
    else { api("GET", "/api/answers").then(function (data) { answerList(wrap, data.answers, lead); }).catch(showError); }
    box.appendChild(wrap);
  }

  function renderTurn(turn, answers) {
    var box = el("turn");
    box.textContent = "";
    el("result").hidden = !(turn && turn.kind === "complete");
    if (!turn) { return; }
    if (turn.kind === "checklist") {
      box.appendChild(text("p", turn.ask, "ask"));
      if (turn.why) { box.appendChild(text("p", turn.why, "why")); }
      var fields = [];
      var list = document.createElement("ul");
      list.className = "ticks";
      (turn.items || []).forEach(function (item) {
        var row = document.createElement("li");
        var label = document.createElement("label");
        var input = document.createElement("input");
        if (item.type === "choice") {
          input = document.createElement("select");
          (item.choices || []).forEach(function (code, i) {
            var o = text("option", (item.labels && item.labels[i]) || code);
            o.value = code;
            input.appendChild(o);
          });
          label.appendChild(text("span", item.label + " "));
          label.appendChild(input);
          row.appendChild(label);
        } else if (item.type === "date") {
          input.type = "date";
          input.required = true;
          label.appendChild(text("span", item.label + " "));
          label.appendChild(input);
          row.appendChild(label);
        } else if (item.type === "amount" || item.type === "text") {
          input.type = "text";
          input.size = item.type === "text" ? 8 : 14;
          label.appendChild(text("span", item.label + " "));
          label.appendChild(input);
          if (item.why) { row.appendChild(label); row.appendChild(text("p", item.why, "why")); }
          else { row.appendChild(label); }
        } else {
          input.type = "checkbox";
          label.appendChild(input);
          label.appendChild(text("span", " " + item.label));
          row.appendChild(label);
        }
        list.appendChild(row);
        fields.push({item: item, input: input});
      });
      box.appendChild(list);
      var done = text("button", "That is everything");
      done.type = "button";
      done.onclick = function () {
        var given = {};
        fields.forEach(function (f) {
          given[f.item.path] = f.item.type === "tick" || !f.item.type ? f.input.checked : f.input.value;
        });
        reply(turn, given);
      };
      box.appendChild(done);
      return;
    }
    if (turn.kind === "more_forms" || turn.kind === "workbook_wait") {
      // Decided 2026-09-28: how many more of each form, 0 until changed; a number above 0 is
      // rows in the workbook, and the page waits for it to be saved and used for the answers.
      var wait = turn.kind === "workbook_wait";
      box.appendChild(text("p", turn.ask, "ask"));
      if (turn.missing && turn.missing.length) {
        var empty = document.createElement("ul");
        turn.missing.forEach(function (m) { empty.appendChild(text("li", m, "ask")); });
        box.appendChild(empty);
      }
      if (turn.why) { box.appendChild(text("p", turn.why, "why")); }
      var counts = [];
      var countList = document.createElement("ul");
      countList.className = "ticks";
      (turn.items || []).forEach(function (item) {
        var row = document.createElement("li");
        var label = document.createElement("label");
        var input = document.createElement("input");
        input.type = "number";
        input.min = "0";
        input.step = "1";
        input.value = item.value || "0";
        input.style.width = "5em";
        input.setAttribute("data-path", item.path);
        label.appendChild(text("span", item.label + " "));
        label.appendChild(input);
        row.appendChild(label);
        countList.appendChild(row);
        counts.push({item: item, input: input});
      });
      box.appendChild(countList);
      var sendCounts = text("button", wait ? "Change the numbers" : "Go on with these numbers", wait ? "quiet" : "");
      sendCounts.type = "button";
      sendCounts.onclick = function () {
        var given = {};
        counts.forEach(function (c) { given[c.item.path] = c.input.value; });
        reply(turn, given);
      };
      if (wait) {
        var look = text("button", "I saved the workbook — look at it now");
        look.type = "button";
        look.onclick = function () {
          showError(null);
          api("GET", "/api/workbook/edited", null, null, "Looking at the workbook").then(function (d) {
            renderWorkbookEdit(d.workbook_edited);
            if (!d.workbook_edited) { showError({message: "The workbook is the same as when this page wrote it. Save it after typing, then look again."}); }
          }).catch(showError);
        };
        box.appendChild(look);
        box.appendChild(document.createTextNode(" "));
      }
      box.appendChild(sendCounts);
      return;
    }
    if (turn.kind === "review") {
      box.appendChild(text("p", turn.ask, "ask"));
      if (turn.why) { box.appendChild(text("p", turn.why, "why")); }
      answerList(box, turn.answers, null);
      var go = text("button", "These are my answers — compute my return");
      go.type = "button";
      go.onclick = function () { reply(turn, "ok"); };
      box.appendChild(go);
      return;
    }
    // a proposal (the residence state from W-2 box 15) is a question with its answer chosen
    var proposal = turn.kind === "confirm" && turn.choices && turn.choices.length;
    if (turn.kind === "confirm" && !proposal) {
      box.appendChild(text("p", turn.ask, "ask"));
      var table = document.createElement("table");
      var head = table.createTHead().insertRow();
      ["Box", "Read as", "Correct it if it is wrong"].forEach(function (h) { head.appendChild(text("th", h)); });
      var inputs = {};
      turn.candidates.forEach(function (c) {
        var row = table.insertRow();
        row.appendChild(text("td", c.caption));
        row.appendChild(text("td", c.raw));
        var cell = row.insertCell();
        var input = document.createElement("input");
        input.type = "text"; input.setAttribute("aria-label", "Correct " + c.caption);
        cell.appendChild(input);
        inputs[c.path] = input;
      });
      box.appendChild(table);
      var asks = [];
      if (turn.items && turn.items.length) {
        var extra = document.createElement("ul");
        extra.className = "ticks";
        turn.items.forEach(function (item) {
          var row = document.createElement("li");
          var label = document.createElement("label");
          var tick = document.createElement("input");
          if (item.type === "choice") {
            // a question that is on no printed box — a Yes / No that starts unchosen
            tick = document.createElement("select");
            (item.choices || []).forEach(function (code, i) {
              var o = text("option", (item.labels && item.labels[i]) || code);
              o.value = code;
              tick.appendChild(o);
            });
            label.appendChild(text("span", item.label + " "));
            label.appendChild(tick);
          } else {
            tick.type = "checkbox";
            label.appendChild(tick);
            label.appendChild(text("span", " " + item.label));
          }
          row.appendChild(label);
          extra.appendChild(row);
          asks.push({path: item.path, input: tick, choice: item.type === "choice"});
        });
        box.appendChild(extra);
      }
      var ok = text("button", "These match the paper");
      ok.type = "button";
      ok.onclick = function () {
        var corrections = {};
        Object.keys(inputs).forEach(function (p) { if (inputs[p].value.trim()) { corrections[p] = inputs[p].value.trim(); } });
        asks.forEach(function (a) { corrections[a.path] = a.choice ? a.input.value : a.input.checked; });
        reply(turn, Object.keys(corrections).length ? corrections : (turn.path ? {} : "all"));
      };
      box.appendChild(ok);
      return;
    }
    if (turn.kind === "question" || proposal) {
      box.appendChild(text("p", turn.ask, "ask"));
      if (turn.why) { box.appendChild(text("p", turn.why, "why")); }
      var field;
      if (turn.choices && turn.choices.length) {
        field = document.createElement("select");
        turn.choices.forEach(function (c) {
          var o = text("option", (turn.choice_labels && turn.choice_labels[c]) || c);
          o.value = c;
          field.appendChild(o);
        });
        if (proposal && turn.candidates && turn.candidates.length) { field.value = turn.candidates[0].value; }
      } else {
        field = document.createElement("input");
        field.type = "text";
      }
      field.setAttribute("aria-label", turn.ask);
      var send = text("button", "Answer");
      send.type = "button";
      send.onclick = function () { reply(turn, field.value); };
      field.addEventListener("keydown", function (e) { if (e.key === "Enter") { send.click(); } });
      box.appendChild(field);
      box.appendChild(send);
      if (turn.optional) {
        var skip = text("button", "Leave it as it is", "quiet");
        skip.type = "button";
        skip.onclick = function () { reply(turn, ""); };
        box.appendChild(skip);
      }
      field.focus();
      return;
    }
    if (turn.kind === "complete") {
      box.appendChild(text("p", "Every question is answered. Your return is below; check it, then fill the forms.", "ask"));
      el("computed-at").textContent = turn.computed_at ? "Last calculated at " + turn.computed_at + ", from the documents and answers listed on this page." : "";
      if (turn.typed && turn.typed.length) {
        // lines typed from a form this version does not read: said with the figures, every time
        var typedList = document.createElement("ul");
        typedList.className = "typed-by-you";
        box.appendChild(text("p", turn.typed[0], "why"));
        turn.typed.slice(1).forEach(function (line) { typedList.appendChild(text("li", line, "why")); });
        box.appendChild(typedList);
      }
      var body = el("lines").tBodies[0];
      body.textContent = "";
      Object.keys(turn.lines || {}).forEach(function (k) {
        var row = body.insertRow();
        row.appendChild(text("td", k));
        row.appendChild(text("td", turn.lines[k]));
      });
      el("result").hidden = false;
      changeAnswer(box, "If one of your answers was not what you meant, change it and the questions continue from there.", answers);
      return;
    }
    if (turn.kind === "refused") {
      box.appendChild(text("p", "This return cannot be computed here:", "ask"));
      var list = document.createElement("ul");
      (turn.refusals || []).forEach(function (r) { list.appendChild(text("li", r)); });
      box.appendChild(list);
      changeAnswer(box, "If one of your answers was not what you meant, change it and the questions continue from there.", answers);
    }
  }

  // A form that reads exactly like one already held is asked about, not counted
  // twice and not refused — the person says whether it is a second form or the same one again.
  function askAboutDuplicate(file, duplicate) {
    var box = document.createElement("div");
    box.className = "duplicate";
    box.appendChild(text("p", duplicate.words, "ask"));
    var again = text("button", "It is a second form — add it");
    again.type = "button";
    again.onclick = function () {
      box.remove();
      file.arrayBuffer().then(function (buf) {
        return api("POST", "/api/documents", buf,
                   {"X-Filename": file.name, "Content-Type": "application/pdf", "X-Add-Anyway": "1"},
                   "Reading " + file.name);
      }).then(refresh).catch(showError);
    };
    var leave = text("button", "It is the same one — leave it out");
    leave.type = "button";
    leave.className = "quiet";
    leave.onclick = function () { box.remove(); };
    box.appendChild(again);
    box.appendChild(document.createTextNode(" "));
    box.appendChild(leave);
    el("reads").appendChild(box);
  }

  function upload(files) {
    showError(null);
    var chain = Promise.resolve();
    Array.prototype.forEach.call(files, function (f) {
      chain = chain.then(function () {
        return f.arrayBuffer().then(function (buf) {
          return api("POST", "/api/documents", buf, {"X-Filename": f.name, "Content-Type": "application/pdf"},
                     "Reading " + f.name, true);
        }).catch(function (e) {
          if (e && e.duplicate) { askAboutDuplicate(f, e.duplicate); return; }
          throw e;
        });
      });
    });
    chain.then(refresh).catch(showError);
  }

  // Decided 2026-09-22: return-workbook.xlsx edited after the page wrote it is noticed and
  // asked about — its figures become the answers only on a yes.
  function renderWorkbookEdit(w) {
    // asked where the person is looking: beside "Compute the workbook again" once the forms are
    // filled (it was pressed once, and the question sat at the top of the page, unseen)
    var here = !el("workbook").hidden;
    var other = el(here ? "workbook-edit" : "workbook-edit-here");
    other.textContent = "";
    other.hidden = true;
    var box = el(here ? "workbook-edit-here" : "workbook-edit");
    box.textContent = "";
    box.hidden = !w;
    if (!w) { return; }
    box.appendChild(text("p", w.name + " in the output folder was changed after this page wrote it" +
      (w.problem ? ", and it cannot be used as it is: " + w.problem + "." : ". Use its figures as your answers?"), "ask"));
    if (w.problem) { return; }
    var list = document.createElement("ul");
    w.changes.forEach(function (c) { list.appendChild(text("li", c, "why")); });
    box.appendChild(list);
    [["Yes — use its figures as my answers", true, ""], ["No — keep my answers as they are", false, "quiet"]].forEach(function (b) {
      var button = text("button", b[0], b[2]);
      button.type = "button";
      button.onclick = function () {
        showError(null);
        api("POST", "/api/workbook/use", JSON.stringify({use: b[1]}), {"Content-Type": "application/json"},
            b[1] ? "Taking the workbook's figures as your answers" : "Keeping your answers")
          .then(function (d) {
            renderWorkbookEdit(d.workbook_edited);
            if (d.turn) { renderTurn(d.turn); showForms(d); refreshDocuments(); }
          }).catch(showError);
      };
      box.appendChild(button);
      box.appendChild(document.createTextNode(" "));
    });
  }

  function refreshDocuments() {
    quiet("/api/state").then(function (s) { renderDocuments(s.documents); }).catch(function () {});
  }

  // The documents already in the chosen folder's input, read where they lie (seen
  // 2026-09-22: the file chooser opened on the folder used last time, whatever folder was chosen —
  // a browser opens it where it last looked, and no page can point it anywhere).
  var inputFolder = "";
  function renderInbox(names) {
    var box = el("inbox");
    box.textContent = "";
    box.hidden = !(names && names.length);
    if (box.hidden) { return; }
    box.appendChild(text("p", "In " + inputFolder + ", not read yet: " + names.join(", ") + ".", "ask"));
    var go = text("button", names.length === 1 ? "Read it" : "Read them");
    go.type = "button";
    go.onclick = function () { readInbox({names: names}); };
    box.appendChild(go);
  }

  function readInbox(ask) {
    showError(null);
    api("POST", "/api/inbox/read", JSON.stringify(ask), {"Content-Type": "application/json"},
        "Reading " + ((ask.names || []).length ? ask.names.length + " document(s)" : "the documents in " + inputFolder), true)
      .then(function (d) {
        renderInbox(d.inbox);
        d.problems.forEach(function (p) { el("reads").appendChild(text("p", p.error, "why")); });
        d.duplicates.forEach(function (dup) {
          var box = document.createElement("div");
          box.className = "duplicate";
          box.appendChild(text("p", dup.words, "ask"));
          var again = text("button", "It is a second form — add it");
          again.type = "button";
          again.onclick = function () { box.remove(); readInbox({names: [dup.name], add_anyway: true}); };
          var leave = text("button", "It is the same one — leave it out");
          leave.type = "button";
          leave.className = "quiet";
          leave.onclick = function () {
            box.remove();
            api("POST", "/api/inbox/leave", JSON.stringify({name: dup.name}), {"Content-Type": "application/json"})
              .then(function (r) { renderInbox(r.inbox); }).catch(showError);
          };
          box.appendChild(again);
          box.appendChild(document.createTextNode(" "));
          box.appendChild(leave);
          el("reads").appendChild(box);
        });
        return refresh();
      }).catch(showError);
  }

  window.addEventListener("focus", function () {
    if (!folderConfirmed) { return; }
    quiet("/api/workbook/edited").then(function (d) { renderWorkbookEdit(d.workbook_edited); }).catch(function () {});
    quiet("/api/inbox").then(function (d) { renderInbox(d.inbox); }).catch(function () {});
  });

  function refresh() {
    return api("GET", "/api/state", null, null, "Loading the page and working out what comes next").then(function (s) {
      if (!folderConfirmed) { renderFolder(s); return; }
      el("tray").hidden = false;
      outputFolder = s.output_folder;
      inputFolder = s.input_windows || s.input_folder;
      el("where").textContent = "Reading from " + s.input_folder + " · writing to " + s.output_folder +
        (s.input_windows ? " (on Windows: " + s.input_windows + ")" : "") +
        ". Documents you put in that input folder are listed here to read. The file chooser opens wherever your browser last looked, not in this folder.";
      // a return this folder already held, picked up where it stopped
      if (s.resumed_at) {
        el("where").textContent += " This folder holds a return you started; it was kept on " +
          s.resumed_at + ", and the answers below are the ones you gave then.";
      }
      if (s.session_problem) { el("where").textContent += " " + s.session_problem; }
      el("resumed").hidden = !s.resumed_at;
      renderReads(s);
      if (s.work_log != null) {
        var area = el("work-log");
        var atEnd = area.scrollTop + area.clientHeight >= area.scrollHeight - 4;
        area.value = s.work_log;
        if (atEnd) { area.scrollTop = area.scrollHeight; }
      }
      renderDocuments(s.documents);
      renderIdentity(s.identity);
      renderNotations(s.notations);
      // figures are shown only when the current turn IS a computed return; a
      // reopened page never shows a return from another time as if it were this one's.
      el("result").hidden = !(s.turn && s.turn.kind === "complete");
      renderTurn(s.turn);
      showForms(s);
      renderWorkbookEdit(s.workbook_edited);
      renderInbox(s.inbox);
      refreshAi();
    }).catch(showError);
  }

  el("files").addEventListener("change", function (e) { upload(e.target.files); });
  // The Windows "Open" window, opened by the program in the working folder's input — the
  // browser's own chooser opens wherever the browser last looked (seen again
  // 2026-09-24). What is chosen is copied into the input folder and read from there.
  el("choose-documents").addEventListener("click", function () {
    showError(null);
    api("POST", "/api/documents/pick", "{}", {"Content-Type": "application/json"},
        "Waiting for you to choose documents in the window that opened", true)
      .then(function (d) {
        if (!d.paths || !d.paths.length) { return; }            // cancelled
        return api("POST", "/api/documents/take", JSON.stringify({paths: d.paths}),
                   {"Content-Type": "application/json"}, "Copying " + d.paths.length + " document(s) into " + inputFolder, true)
          .then(function (t) {
            t.problems.forEach(function (p) { el("reads").appendChild(text("p", p.error, "why")); });
            if (t.names.length) { readInbox({names: t.names}); }
          });
      })
      .catch(function (e) {
        if (e && /no Windows folder picker|could not be opened/.test(e.message || "")) { el("files").click(); }
        else { showError(e); }
      });
  });
  var drop = document.querySelector(".drop");
  drop.addEventListener("dragover", function (e) { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", function () { drop.classList.remove("over"); });
  drop.addEventListener("drop", function (e) { e.preventDefault(); drop.classList.remove("over"); upload(e.dataTransfer.files); });
  el("fill").addEventListener("click", function () {
    showError(null);
    api("POST", "/api/fill", null, null, "Computing again, filling the IRS forms and checking every box").then(function (d) {
      el("filled").textContent = "";
      d.filled.forEach(function (n) { el("filled").appendChild(text("li", inFolder(d.folder, n))); });
      (d.stated || []).forEach(function (s) { el("filled").appendChild(text("li", s, "why")); });
      if (d.lint) { el("filled").appendChild(text("li", "Checked: " + d.lint.words, d.lint.defects ? "" : "why")); }
      if (d.filled.length) {
        el("filled").appendChild(text("li", "Open that folder to print or check them.", "why"));
      }
      if (d.workbook) {
        el("filled").appendChild(text("li", inFolder(d.folder, d.workbook)));
        el("workbook").hidden = false;
      }
      if (d.workbook_problem) { el("filled").appendChild(text("li", d.workbook_problem)); }
      if (d.check_started) {
        el("filled").appendChild(text("li", "A local AI model has started checking the filled forms; its progress is in the section above.", "why"));
      }
      refreshAi();
    }).catch(showError);
  });
  el("work-log-copy").addEventListener("click", function () {
    var area = el("work-log"), note = el("work-log-note");
    area.focus();
    area.select();
    var done = function () { note.textContent = "Copied."; };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(area.value).then(done, function () {
        note.textContent = document.execCommand("copy") ? "Copied." : "Selected; press Ctrl+C to copy.";
      });
    } else {
      note.textContent = document.execCommand("copy") ? "Copied." : "Selected; press Ctrl+C to copy.";
    }
  });

  el("session-restart").addEventListener("click", function () {
    showError(null);
    api("POST", "/api/session", null, null, "Starting this folder again").then(function (d) {
      el("session-note").textContent = d.set_aside
        ? "The return you had is kept as " + d.set_aside + "; this folder starts again."
        : "This folder starts again.";
      refresh();
    }).catch(showError);
  });

  el("workbook-run").addEventListener("click", function () {
    showError(null);
    el("workbook-note").textContent = "";
    api("POST", "/api/workbook", null, null, "Computing the workbook again").then(function (d) {
      el("workbook-note").textContent = "Computed again: " + d.workbook + ". Open it to see the Computed return tab.";
      quiet("/api/workbook/edited").then(function (w) { renderWorkbookEdit(w.workbook_edited); }).catch(function () {});
    }).catch(showError);
  });
  el("about-link").href = "about?t=" + encodeURIComponent(token);
  el("quit").addEventListener("click", function () {
    api("POST", "/api/quit", null, null, "Stopping").then(function () {
      el("quit").disabled = true;
      el("quit-note").textContent = "ytax-prep has stopped. You can close this tab; your folder keeps everything for next time.";
    }).catch(showError);
  });
  // The packaged app stops on its own once no page is open. This page checks in
  // twice a minute and when it comes back into view, and says it is going when its tab closes; a
  // reload's new page checks in at once. A beacon carries no header, so its token is in the address.
  function stillHere() {
    fetch("/api/alive", {method: "POST", headers: {"X-Intake-Token": token}}).catch(function () {});
  }
  setInterval(stillHere, 30000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) { stillHere(); } });
  window.addEventListener("pageshow", stillHere);
  window.addEventListener("pagehide", function () {
    if (navigator.sendBeacon) { navigator.sendBeacon("/api/closing?t=" + encodeURIComponent(token)); }
  });
  refresh();
})();
