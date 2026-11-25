/* Boombaland website: the one config spot for the store links, and the screenshot lightbox. No trackers, no cookies. */
(function () {
  "use strict";

  // ---- CONFIG: filled in on launch day by tools/go_live.py (see GO_LIVE.md, "Launch day"); then rebuild. ---------------
  // While a URL is empty, its button stays a "Coming soon" label that links to nothing.
  var STORE_LINKS = {
    ios: "https://apps.apple.com/app/id6821619320",      // TODO: https://apps.apple.com/app/id<APPLE_ID> (the numeric Apple ID from App Store Connect, App Information)
    android: "https://play.google.com/store/apps/details?id=com.datasight.boomworld"   // TODO: https://play.google.com/store/apps/details?id=com.datasight.boomworld (fill in on launch day)
  };
  // -------------------------------------------------------------------------------------------------------------------

  // tools/build.py renders the buttons from this same config (status planks while empty, badges once filled), so this only
  // patches links that are anchors already.
  document.querySelectorAll("a[data-store]").forEach(function (a) {
    var url = STORE_LINKS[a.getAttribute("data-store")];
    if (url) {
      a.href = url;
      a.removeAttribute("aria-disabled");
      var note = a.querySelector("[data-store-note]");
      if (note) note.textContent = "Free download";
    }
  });
  document.querySelectorAll('[data-store][aria-disabled="true"]').forEach(function (a) {
    a.addEventListener("click", function (e) { e.preventDefault(); });
  });

  // ---- Lightbox for the screenshot gallery (falls back to opening the image when <dialog> is missing). ------------
  var dialog = document.getElementById("lightbox");
  if (!dialog || typeof dialog.showModal !== "function") return;
  var img = dialog.querySelector("img");
  var cap = dialog.querySelector("p");
  var lastFocus = null;
  document.querySelectorAll("[data-lightbox]").forEach(function (a) {
    a.addEventListener("click", function (e) {
      e.preventDefault();
      lastFocus = a;
      var thumb = a.querySelector("img");
      img.src = a.getAttribute("href");
      img.alt = thumb ? thumb.alt : "";
      cap.textContent = a.getAttribute("data-caption") || "";
      dialog.showModal();
    });
  });
  dialog.querySelector("button").addEventListener("click", function () { dialog.close(); });
  dialog.addEventListener("click", function (e) { if (e.target === dialog) dialog.close(); });
  dialog.addEventListener("close", function () { img.removeAttribute("src"); if (lastFocus) lastFocus.focus(); });
})();

/* Gameplay clips: muted, looping, played only while on screen; under prefers-reduced-motion the poster stays. */
(function () {
  "use strict";
  var vids = document.querySelectorAll("video[data-clip]");
  if (!vids.length) return;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce || !("IntersectionObserver" in window)) return;
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      var v = e.target;
      if (e.isIntersecting) {
        if (v.preload !== "auto") { v.preload = "auto"; v.autoplay = true; }
        var p = v.play(); if (p && p.catch) p.catch(function () {});
      } else { v.pause(); }
    });
  }, { rootMargin: "200px 0px" });
  vids.forEach(function (v) { v.muted = true; io.observe(v); });
})();

/* The trailer: a poster link until pressed, then YouTube's privacy-enhanced player (no YouTube request before the click). */
(function () {
  "use strict";
  document.querySelectorAll("[data-trailer]").forEach(function (box) {
    var a = box.querySelector("a");
    a.addEventListener("click", function (e) {
      e.preventDefault();
      var f = document.createElement("iframe");
      f.src = "https://www.youtube-nocookie.com/embed/" + box.getAttribute("data-trailer") + "?autoplay=1&rel=0&playsinline=1";
      f.title = "Boombaland trailer";
      f.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
      f.allowFullscreen = true;
      box.replaceChildren(f);
    });
  });
})();

/* Press kit: "Copy the text" copies the approved short description (no clipboard library, no permission prompt). */
(function () {
  "use strict";
  document.querySelectorAll("button[data-copy]").forEach(function (b) {
    var src = document.getElementById(b.getAttribute("data-copy"));
    var done = b.parentNode.querySelector(".copy-done");
    if (!src) return;
    var say = function (t) { if (done) done.textContent = t; };
    var fallback = function () {  // no clipboard API: select the text so the reader can copy it
      var r = document.createRange(); r.selectNodeContents(src);
      var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
      say("Selected: copy it with your keyboard or menu.");
    };
    b.addEventListener("click", function () {
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(src.textContent.trim()).then(function () { say("Copied."); }, fallback);
      } else { fallback(); }
    });
  });
})();
