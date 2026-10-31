/* Wiki: side nav open on wide screens (a collapsible <details> on phones) and a small client-side search over
   /wiki/search.json (written by tools/build_wiki.py). No external requests. */
(function () {
  "use strict";
  var nav = document.getElementById("wiki-nav");
  if (nav && window.matchMedia("(min-width: 900px)").matches) nav.open = true;

  var q = document.getElementById("wiki-q"), out = document.getElementById("wiki-results"), index = null;
  if (!q || !out) return;
  function load(cb) {
    if (index) return cb();
    fetch("/wiki/search.json").then(function (r) { return r.json(); }).then(function (j) { index = j; cb(); })
      .catch(function () { index = []; cb(); });
  }
  function esc(s) { return s.replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function search() {
    var terms = q.value.toLowerCase().split(/\s+/).filter(Boolean);
    out.innerHTML = "";
    if (!terms.length) return;
    var hits = index.map(function (p) {
      var t = p.t.toLowerCase(), h = p.h.join(" ").toLowerCase(), x = p.x.toLowerCase(), score = 0;
      for (var i = 0; i < terms.length; i++) {
        var w = terms[i], s = (t.indexOf(w) >= 0 ? 10 : 0) + (h.indexOf(w) >= 0 ? 5 : 0) + (x.indexOf(w) >= 0 ? 1 : 0);
        if (!s) return null;
        score += s;
      }
      var at = x.indexOf(terms[0]), snip = at >= 0 ? p.x.substr(Math.max(0, at - 40), 120) : "";
      return { p: p, s: score, snip: snip };
    }).filter(Boolean).sort(function (a, b) { return b.s - a.s; }).slice(0, 8);
    if (!hits.length) { out.innerHTML = "<li class=\"none\">No results</li>"; return; }
    out.innerHTML = hits.map(function (r) {
      return "<li><a href=\"" + r.p.u + "\">" + esc(r.p.t) + "</a>" + (r.snip ? "<small>…" + esc(r.snip) + "…</small>" : "") + "</li>";
    }).join("");
  }
  q.addEventListener("input", function () { load(search); });
  q.addEventListener("focus", function () { load(function () {}); });
})();
