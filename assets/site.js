/* Boombaland website: the one config spot for the store links, and the screenshot lightbox. No trackers, no cookies. */
(function () {
  "use strict";

  // ---- CONFIG: fill these in once the store pages are live (see GO_LIVE.md, step 4). ----------------------------------
  // While a URL is empty, its button stays a "Coming 19 November" label that links to nothing.
  var STORE_LINKS = {
    ios: "",      // TODO: https://apps.apple.com/app/id<APPLE_ID> (the numeric Apple ID from App Store Connect, App Information)
    android: ""   // TODO: https://play.google.com/store/apps/details?id=com.datasight.boomworld (fill in on launch day)
  };
  // -------------------------------------------------------------------------------------------------------------------

  document.querySelectorAll("[data-store]").forEach(function (a) {
    var url = STORE_LINKS[a.getAttribute("data-store")];
    if (url) {
      a.href = url;
      a.removeAttribute("aria-disabled");
      var note = a.querySelector("[data-store-note]");
      if (note) note.textContent = "Download now";
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
