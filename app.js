/* Shared catalog: filter chips, search, sortable columns, and chart rows.
   Needs compare.js (loaded first) for cell helpers and the Compare checkboxes. */
(function () {
  var U = window.WPCompare.util, esc = U.esc, has = U.has, NA = U.NA;
  var BAND_MID = { "$": 60, "$$": 175, "$$$": 425, "$$$$": 1050, "$$$$$": 2000 };

  function num(v) { return has(v) ? Number(v) : null; }
  function txt(v) { return has(v) ? esc(v) : NA; }
  function unitCell(v) { return has(v) ? esc(U.fmtNum(v)) : NA; }

  // Column registry. s = sort value fn (numbers or strings; empty sorts last).
  var COLS = {
    brand: { cls: "brandc", s: function (d) { return d.brand; },
      cell: function (d) {
        return U.badge(d, true) + '<label class="cmp"><input type="checkbox" class="cmp-cb" data-id="' + esc(d.id) + '"> Compare</label>';
      } },
    model: { cls: "modelc", s: function (d) { return (d.model || "") || (d.series || ""); },
      cell: function (d) {
        var main = d.model || d.series, ser = d.model && d.series && d.series !== d.model ? d.series : "";
        if (!main && !d.name) return NA;
        return '<span class="cart">' + esc(main || d.name) + "</span>" + (ser ? '<span class="ser">' + esc(ser) + "</span>" : "") +
          (main && d.name ? '<span class="sub">' + esc(d.name) + "</span>" : "") +
          (d.notes ? '<span class="sub note">' + esc(d.notes) + "</span>" : "");
      } },
    type: { cls: "typec", s: function (d) { return d.type; }, cell: function (d) { return txt(d.type); } },
    cls: { cls: "clsc", s: function (d) { return d.ansi_class; }, cell: function (d) { return txt(d.ansi_class); } },
    standards: { cls: "stdc", s: function (d) { return (d.standards || []).join(" "); },
      cell: function (d) { return U.stdHtml(d.standards) || NA; } },
    capacity: { cls: "num", num: 1, s: function (d) { return num(has(d.cap_max_lb) ? d.cap_max_lb : d.cap_min_lb); },
      cell: function (d) { var t = U.capTxt(d); return t ? esc(t) : NA; } },
    length: { cls: "num", num: 1, s: function (d) { return num(d.length_ft); }, cell: function (d) { return unitCell(d.length_ft); } },
    weight: { cls: "num", num: 1, s: function (d) { return num(d.weight_lb); }, cell: function (d) { return unitCell(d.weight_lb); } },
    gate: { cls: "num", num: 1, s: function (d) { return num(d.gate_lbf); }, cell: function (d) { return unitCell(d.gate_lbf); } },
    attachment: { cls: "attc", s: function (d) { return d.attachment; }, cell: function (d) { return txt(d.attachment); } },
    material: { cls: "matc", s: function (d) { return d.material; }, cell: function (d) { return txt(d.material); } },
    sizes: { cls: "sizec", s: function (d) { return d.sizes; }, cell: function (d) { return txt(d.sizes); } },
    features: { cls: "featc", s: function (d) { return d.features; }, cell: function (d) { return txt(d.features); } },
    price: { cls: "nw", num: 1, price: 1,
      s: function (d) { return has(d.price_usd) ? Number(d.price_usd) : (BAND_MID[d.price_scale] || null); },
      cell: function (d) { return U.priceHtml(d); } },
    links: { cls: "", cell: function (d) { return U.linksHtml(d); } }
  };

  function stdHas(d, re) { return (d.standards || []).some(function (s) { return re.test(s); }); }
  function classTokens(d) {
    if (!has(d.ansi_class)) return [];
    return String(d.ansi_class).split(/\s*[,;]\s*/).filter(Boolean).map(function (t) {
      return /^[A-Z]$/.test(t) ? "Class " + t : t;
    });
  }
  // Filter groups. values(DATA) -> [{v,label}], test(d,v).
  var GROUPS = {
    brand: { label: "Brand", values: function (D) { return distinct(D, function (d) { return d.brand; }); }, test: function (d, v) { return d.brand === v; } },
    type: { label: "Type", values: function (D) { return distinct(D, function (d) { return d.type; }); }, test: function (d, v) { return d.type === v; } },
    cls: { label: "Class", values: function (D) {
        var all = []; D.forEach(function (d) { all = all.concat(classTokens(d)); });
        return distinct(all.map(function (t) { return { t: t }; }), function (x) { return x.t; });
      }, test: function (d, v) { return classTokens(d).indexOf(v) !== -1; } },
    ansi: { label: "ANSI Z359", values: function () { return [{ v: "y", label: "ANSI Z359 listed" }, { v: "n", label: "Not stated" }]; },
      test: function (d, v) { return stdHas(d, /Z359/i) === (v === "y"); } },
    csa: { label: "CSA Z259", values: function () { return [{ v: "y", label: "CSA Z259 listed" }, { v: "n", label: "Not stated" }]; },
      test: function (d, v) { return stdHas(d, /CSA|Z259/i) === (v === "y"); } },
    cap: { label: "Capacity", values: function () { return [{ v: "std", label: "Up to 310 lb" }, { v: "hi", label: "Over 310 lb" }]; },
      test: function (d, v) { return has(d.cap_max_lb) && (v === "hi" ? Number(d.cap_max_lb) > 310 : Number(d.cap_max_lb) <= 310); } }
  };
  function distinct(D, f) {
    var seen = {}, out = [];
    D.forEach(function (d) { var v = f(d); if (has(v) && !seen[v]) { seen[v] = 1; out.push({ v: v, label: v }); } });
    return out.sort(function (a, b) { return a.label.localeCompare(b.label, undefined, { numeric: true }); });
  }
  function norm(s) { return String(s == null ? "" : s).toLowerCase(); }

  window.initCatalog = function (DATA, opts) {
    var cols = opts.cols, noun = opts.noun || "items", state = { sort: opts.defaultSort || "brand", dir: "asc", f: {}, q: "" };
    var rowsEl = document.getElementById("rows"), countEl = document.getElementById("count");
    if (!rowsEl) return;
    var LBL = opts.labels || {};

    // ---- filter chips ----
    var fwrap = document.getElementById("fgroups"), shown = [];
    (opts.filters || []).forEach(function (gk) {
      var g = GROUPS[gk];
      if (!g) return;
      var vals = g.values(DATA).map(function (o) {
        return { v: o.v, label: o.label, n: DATA.filter(function (d) { return g.test(d, o.v); }).length };
      }).filter(function (o) { return o.n > 0; });
      if (vals.length < 2) return;
      shown.push(gk);
      var div = document.createElement("div");
      div.className = "fgroup";
      div.innerHTML = '<span class="flabel">' + esc(g.label) + '</span><div class="chips" role="group" aria-label="' + esc(g.label) + '">' +
        '<button type="button" class="chip" data-g="' + gk + '" data-v="" aria-pressed="true">All</button>' +
        vals.map(function (o) { return '<button type="button" class="chip" data-g="' + gk + '" data-v="' + esc(o.v) + '" aria-pressed="false">' + esc(o.label) + "<small>" + o.n + "</small></button>"; }).join("") +
        "</div>";
      fwrap.appendChild(div);
    });
    fwrap.addEventListener("click", function (ev) {
      var b = ev.target.closest(".chip");
      if (!b) return;
      var g = b.getAttribute("data-g"), v = b.getAttribute("data-v");
      if (v) state.f[g] = v; else delete state.f[g];
      b.parentNode.querySelectorAll(".chip").forEach(function (c) { c.setAttribute("aria-pressed", c === b ? "true" : "false"); });
      render();
    });
    function resetFilters() {
      state.f = {}; state.q = "";
      document.querySelectorAll(".chip").forEach(function (c) { c.setAttribute("aria-pressed", c.getAttribute("data-v") === "" ? "true" : "false"); });
      var s = document.getElementById("search"); if (s) s.value = "";
    }

    // ---- sort control ----
    var sel = document.getElementById("sort");
    if (sel) {
      var o = [];
      cols.forEach(function (k) {
        var c = COLS[k];
        if (!c || !c.s) return;
        var L = LBL[k] || k, lab = c.price ? ["Price: cheapest first", "Price: priciest first"] : c.num ? [L + ": low → high", L + ": high → low"] : [L + ": A → Z", L + ": Z → A"];
        o.push('<option value="' + k + ':asc">' + esc(lab[0]) + '</option><option value="' + k + ':desc">' + esc(lab[1]) + "</option>");
      });
      sel.innerHTML = o.join("");
      sel.addEventListener("change", function () { var p = sel.value.split(":"); state.sort = p[0]; state.dir = p[1]; render(); });
    }
    document.querySelectorAll(".th-btn").forEach(function (b) {
      b.addEventListener("click", function () {
        var k = b.getAttribute("data-k");
        if (state.sort === k) state.dir = state.dir === "asc" ? "desc" : "asc";
        else { state.sort = k; state.dir = "asc"; }
        render();
      });
    });
    var search = document.getElementById("search");
    if (search) search.addEventListener("input", function () { state.q = norm(search.value.trim()); render(); });

    function matches(d) {
      for (var g in state.f) if (!GROUPS[g].test(d, state.f[g])) return false;
      if (!state.q) return true;
      var blob = norm([d.brand, d.series, d.model, d.name, d.type, d.ansi_class, (d.standards || []).join(" "), d.attachment, d.material, d.sizes, d.features, d.notes].join(" "));
      return state.q.split(/\s+/).every(function (w) { return blob.indexOf(w) !== -1; });
    }
    function sorted(rows) {
      var c = COLS[state.sort], dir = state.dir === "desc" ? -1 : 1;
      if (!c || !c.s) return rows;
      return rows.slice().sort(function (a, b) {
        var x = c.s(a), y = c.s(b), bx = !has(x), by = !has(y);
        if (bx || by) return bx && by ? 0 : bx ? 1 : -1; // blanks always last
        var r = c.num ? x - y : String(x).localeCompare(String(y), undefined, { numeric: true, sensitivity: "base" });
        return r * dir || String(a.brand).localeCompare(String(b.brand)) || String(a.model).localeCompare(String(b.model), undefined, { numeric: true });
      });
    }
    function syncControls() {
      if (sel) { var v = state.sort + ":" + state.dir; if ([].some.call(sel.options, function (x) { return x.value === v; })) sel.value = v; }
      document.querySelectorAll(".th-btn").forEach(function (b) {
        if (b.getAttribute("data-k") === state.sort) b.setAttribute("data-dir", state.dir); else b.removeAttribute("data-dir");
      });
    }
    function row(d) {
      return '<tr id="' + esc(d.rid) + '">' + cols.map(function (k) {
        var c = COLS[k];
        return '<td class="' + c.cls + '">' + c.cell(d, opts) + "</td>";
      }).join("") + "</tr>";
    }
    function render() {
      var rows = sorted(DATA.filter(matches));
      rowsEl.innerHTML = rows.map(row).join("") ||
        '<tr><td colspan="' + cols.length + '" class="empty">' + (DATA.length ? "Nothing matches those filters. Clear the search or choose All." : "No rows yet.") + "</td></tr>";
      if (countEl) countEl.textContent = DATA.length ? "Showing " + rows.length + " of " + DATA.length + " " + noun : "0 " + noun + " — no rows yet";
      syncControls();
      window.WPCompare.sync();
    }

    // Deep links: section.html#p-id scrolls to that row and flashes it.
    function focusHash(smooth) {
      var id = decodeURIComponent((location.hash || "").slice(1));
      if (!id || !/^p-/.test(id) || !DATA.some(function (d) { return d.rid === id; })) return;
      var tr = document.getElementById(id);
      if (!tr) { resetFilters(); render(); tr = document.getElementById(id); }
      if (!tr) return;
      var box = tr.closest(".table-box");
      if (box) {
        // The chart scrolls inside its own box, so scroll the box, then bring the box into view.
        box.scrollLeft = 0;
        box.scrollTop = Math.max(0, tr.offsetTop - 44);
        var nav = document.querySelector(".topnav"), navH = nav ? nav.getBoundingClientRect().height : 0;
        window.scrollTo({ top: Math.max(0, box.getBoundingClientRect().top + window.pageYOffset - navH - 70), behavior: smooth ? "smooth" : "instant" });
      }
      document.querySelectorAll("tr.row-flash").forEach(function (r) { r.classList.remove("row-flash"); });
      void tr.offsetWidth;
      tr.classList.add("row-flash");
      setTimeout(function () { tr.classList.remove("row-flash"); }, 3200);
    }
    render();
    if (location.hash) focusHash(false);
    window.addEventListener("hashchange", function () { focusHash(true); });
  };
})();
