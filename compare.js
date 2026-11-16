/* Compare selections (max 4, kept in localStorage across pages), the floating
   "Compare (n)" bar, shared cell helpers, and the side-by-side compare page. */
(function () {
  var KEY = "wp-compare", MAX = 4;
  var NA = '<span class="na" title="Not published / not found">—</span>';
  var listeners = [];

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function has(v) { return v !== null && v !== undefined && v !== "" && !(typeof v === "number" && isNaN(v)); }
  function fmtNum(n) { return Number(n).toLocaleString("en-US", { maximumFractionDigits: 2 }); }
  function fmtDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
    if (!m) return iso || "";
    var mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][Number(m[2]) - 1];
    return mon + " " + Number(m[3]) + ", " + m[1];
  }
  function capTxt(d) {
    var lo = has(d.cap_min_lb), hi = has(d.cap_max_lb);
    if (lo && hi) return fmtNum(d.cap_min_lb) + "–" + fmtNum(d.cap_max_lb) + " lb";
    if (hi) return "up to " + fmtNum(d.cap_max_lb) + " lb";
    if (lo) return "from " + fmtNum(d.cap_min_lb) + " lb";
    return null;
  }
  function unit(v, u) { return has(v) ? fmtNum(v) + " " + u : null; }
  function stdHtml(a) {
    if (!a || !a.length) return "";
    return '<span class="stds">' + a.map(function (s) { return '<span class="std">' + esc(s) + "</span>"; }).join("") + "</span>";
  }
  function hue(s) {
    var h = 0;
    for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
    return 175 + (h % 60);
  }
  function badge(d, withName) {
    if (d._icon) {
      return '<img class="brand-icon" src="' + esc(d._icon) + '" alt="' + esc(d.brand) + '" height="30" loading="lazy">' +
        (withName ? '<span class="brand-name">' + esc(d.brand) + "</span>" : "");
    }
    return '<span class="brand-badge" style="--h:' + hue(String(d.brand || "")) + '">' + esc(d.brand || "Unknown") + "</span>";
  }
  var BANDS = "$ under $100 · $$ $100–$250 · $$$ $250–$600 · $$$$ $600–$1,500 · $$$$$ over $1,500";
  function priceHtml(d) {
    if (has(d.price_usd)) {
      var n = Number(d.price_usd), txt = "$" + (n % 1 ? n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : fmtNum(n));
      var lbl = "Source · checked " + fmtDate(d.price_checked);
      var link = d.price_url
        ? '<a class="src" href="' + esc(d.price_url) + '" target="_blank" rel="noopener noreferrer" title="' + esc(d.price_source || "Retailer listing") + '">' + esc(lbl) + "</a>"
        : '<span class="src">' + esc(lbl) + "</span>";
      return '<span class="price-v">' + esc(txt) + '</span><span class="sub">' + link + "</span>";
    }
    if (has(d.price_scale)) {
      return '<span class="band" title="' + esc(BANDS) + '">' + esc(d.price_scale) + '</span><span class="sub est">Editorial estimate</span>';
    }
    return NA;
  }
  function linksHtml(d) {
    var out = [], L = function (u, t) { return '<a href="' + esc(u) + '" target="_blank" rel="noopener noreferrer">' + t + "</a>"; };
    if (d.product_url) out.push(L(d.product_url, "Official page" + (d.spec_url === d.product_url ? '<span class="off">spec source</span>' : "")));
    if (d.spec_url && d.spec_url !== d.product_url) out.push(L(d.spec_url, "Spec source"));
    if (has(d.price_usd) && d.price_url) out.push(L(d.price_url, "Price: " + esc(d.price_source || "seller")));
    return out.length ? '<div class="links">' + out.join("") + "</div>" : '<span class="na" title="No source recorded">No source</span>';
  }

  // ---- selection state ----
  function read() {
    try {
      var a = JSON.parse(localStorage.getItem(KEY) || "[]");
      return Array.isArray(a) ? a.filter(function (s) { return typeof s === "string"; }).slice(0, MAX) : [];
    } catch (e) { return []; }
  }
  var cur = read();
  function save() { try { localStorage.setItem(KEY, JSON.stringify(cur)); } catch (e) {} }
  function changed() { render(); sync(); listeners.forEach(function (f) { f(cur.slice()); }); }
  var API = {
    max: MAX,
    list: function () { return cur.slice(); },
    has: function (id) { return cur.indexOf(id) !== -1; },
    full: function () { return cur.length >= MAX; },
    add: function (id) { if (cur.indexOf(id) === -1 && cur.length < MAX) { cur.push(id); save(); changed(); return true; } return cur.indexOf(id) !== -1; },
    remove: function (id) { cur = cur.filter(function (x) { return x !== id; }); save(); changed(); },
    clear: function () { cur = []; save(); changed(); },
    setList: function (a) { cur = a.slice(0, MAX); save(); changed(); },
    onChange: function (f) { listeners.push(f); },
    sync: function () { sync(); },
    util: { esc: esc, has: has, NA: NA, fmtNum: fmtNum, fmtDate: fmtDate, capTxt: capTxt, stdHtml: stdHtml, badge: badge, priceHtml: priceHtml, linksHtml: linksHtml }
  };
  window.WPCompare = API;

  function sync() {
    document.querySelectorAll(".cmp-cb").forEach(function (cb) {
      var on = cur.indexOf(cb.getAttribute("data-id")) !== -1;
      cb.checked = on;
      cb.disabled = !on && cur.length >= MAX;
      cb.title = cb.disabled ? "Compare is limited to " + MAX + " items — remove one first" : "";
    });
  }

  // ---- floating bar + nav count ----
  var bar = null, page = document.body.getAttribute("data-page");
  function render() {
    document.querySelectorAll(".cmp-n").forEach(function (n) { n.textContent = cur.length; n.hidden = !cur.length; });
    if (page === "compare") return;
    if (!bar) {
      bar = document.createElement("div");
      bar.className = "cmp-bar";
      bar.setAttribute("role", "region");
      bar.setAttribute("aria-label", "Compare selection");
      bar.innerHTML = '<a class="cmp-go" href="compare.html"></a><button type="button" class="cmp-clear">Clear</button><span class="cmp-msg" role="status"></span>';
      document.body.appendChild(bar);
      bar.querySelector(".cmp-clear").addEventListener("click", function () { API.clear(); });
    }
    bar.hidden = !cur.length;
    bar.querySelector(".cmp-go").textContent = "Compare (" + cur.length + ") →";
    bar.querySelector(".cmp-msg").textContent = cur.length >= MAX ? "Max " + MAX + " — remove one to add another" : "";
  }

  document.addEventListener("change", function (ev) {
    var cb = ev.target;
    if (!cb || !cb.classList || !cb.classList.contains("cmp-cb")) return;
    var id = cb.getAttribute("data-id");
    if (cb.checked) { if (!API.add(id)) cb.checked = false; } else API.remove(id);
  });
  window.addEventListener("storage", function (ev) {
    if (ev.key === KEY) { cur = read(); changed(); }
  });

  // ---- compare page ----
  function E(k) { return [k[0], function (d) { return esc(d[k[1]]); }, function (d) { return d[k[1]]; }]; }
  function N(lbl, k, u) { return [lbl, function (d) { return esc(unit(d[k], u)); }, function (d) { return d[k]; }]; }
  var FIELDS = [
    ["Brand", function (d) { return badge(d, true); }, function (d) { return d.brand; }],
    ["Catalog", function (d) { return '<a href="' + esc(d.sectionFile) + "#" + esc(d.rid) + '">' + esc(d.sectionLabel) + "</a>"; }, function (d) { return d.sectionLabel; }],
    E(["Series", "series"]), E(["Model / part no.", "model"]), E(["Name", "name"]), E(["Type", "type"]),
    ["Standards", function (d) { return stdHtml(d.standards); }, function (d) { return (d.standards || []).length ? 1 : null; }],
    E(["Class / rating", "ansi_class"]),
    ["Capacity", function (d) { return esc(capTxt(d)); }, function (d) { return capTxt(d); }],
    N("Length", "length_ft", "ft"), N("Weight", "weight_lb", "lb"),
    E(["Attachment / connectors", "attachment"]), N("Gate strength", "gate_lbf", "lbf"),
    E(["Material", "material"]), E(["Sizes", "sizes"]), E(["Features", "features"]),
    ["Price", priceHtml, function () { return true; }],
    ["Price source", function (d) { return has(d.price_usd) && d.price_source ? esc(d.price_source) : null; }, function (d) { return has(d.price_usd) ? d.price_source : null; }],
    E(["Notes", "notes"]),
    ["Links", function (d) { return linksHtml(d); }, function () { return true; }]
  ];

  function renderComparePage() {
    var root = document.getElementById("cmp-root");
    if (!root) return;
    var items = window.WP_ITEMS || {};
    var ids = cur.filter(function (id) { return items[id]; });
    if (ids.length !== cur.length) { cur = ids; save(); }
    render();
    var clear = document.getElementById("cmp-clear");
    if (clear) clear.hidden = !ids.length;
    if (!ids.length) {
      root.innerHTML = '<div class="cmp-empty"><p><strong>Nothing selected yet.</strong> Tick “Compare” on up to ' + MAX + ' rows in any of the catalogs, then come back here to see them side by side.</p>' +
        '<p>' + (window.WP_SECTIONS || []).map(function (s) { return '<a href="' + esc(s.file) + '">' + esc(s.label) + "</a>"; }).join(" · ") + "</p></div>";
      return;
    }
    var ds = ids.map(function (id) { return items[id]; });
    var h = '<table class="cmp-table"><thead><tr><th class="rowh" scope="col">Item</th>' + ds.map(function (d) {
      return '<th scope="col">' + badge(d, false) + '<span class="cart" style="margin-top:6px">' + esc(d.model || d.series || d.id) + '</span>' +
        '<span class="ser">' + esc(d.brand) + " · " + esc(d.sectionLabel) + '</span>' +
        '<button type="button" class="rm" data-id="' + esc(d.id) + '">Remove</button></th>';
    }).join("") + "</tr></thead><tbody>";
    FIELDS.forEach(function (f) {
      if (!ds.some(function (d) { return has(f[2](d)); })) return; // skip rows blank for every selected item
      h += '<tr><th class="rowh" scope="row">' + esc(f[0]) + "</th>" + ds.map(function (d) {
        var v = f[1](d);
        return "<td>" + (v === "" || v == null || v === "null" ? NA : v) + "</td>";
      }).join("") + "</tr>";
    });
    h += "</tbody></table>";
    root.innerHTML = h;
  }
  document.addEventListener("click", function (ev) {
    var b = ev.target.closest && ev.target.closest(".rm");
    if (b) API.remove(b.getAttribute("data-id"));
  });
  API.onChange(renderComparePage);

  function init() {
    render(); sync(); renderComparePage();
    var clear = document.getElementById("cmp-clear");
    if (clear) clear.addEventListener("click", function () { API.clear(); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
