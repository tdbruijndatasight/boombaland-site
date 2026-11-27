/* /get/: the one download link for social bios. tools/build.py inlines this file at the end of get/index.html and fills
   in the two store URLs (STORE_LINKS) and the App Store provider token. tools/qa.py runs it in node against fake phones.
   iPhone/iPad -> the App Store, Android -> Google Play, anything else stays on the page (badges + QR code). It can
   navigate ONLY to those two store URLs. An optional ?s=<source> (a-z 0-9 - _, max 24, anything else dropped) tags the
   store links so installs per bio can be told apart. No cookies, no storage, no requests of its own. ES5 on purpose. */
(function (w) {
  "use strict";
  var IOS = "__IOS__";
  var PLAY = "__PLAY__";
  var PT = "__PT__"; // App Store Connect provider token (pt=); Apple ignores ct without it

  function source(search) {
    var m = /[?&]s=([^&#]*)/.exec(search || "");
    return m && /^[a-z0-9_-]{1,24}$/.test(m[1]) ? m[1] : "";
  }

  function storeUrl(store, s) {
    if (store === "ios") return IOS + (s ? "?ct=" + s + (PT ? "&pt=" + PT + "&mt=8" : "") : "");
    if (store === "android") {
      return PLAY + (s ? "&referrer=" + encodeURIComponent("utm_source=" + s + "&utm_medium=social&utm_campaign=bio") : "");
    }
    return "";
  }

  function platform(ua, plat, touch) {
    if (/iPhone|iPad|iPod/.test(ua)) return "ios";
    if (plat === "MacIntel" && touch > 1) return "ios"; // iPadOS asks for the desktop site and reports a Mac
    if (/Android/.test(ua)) return "android";
    return "";
  }

  w.boombalandGet = { source: source, storeUrl: storeUrl, platform: platform };
  var s = source(w.location.search);
  var links = w.document.querySelectorAll("a[data-get]");
  for (var i = 0; i < links.length; i++) links[i].href = storeUrl(links[i].getAttribute("data-get"), s);
  var n = w.navigator || {};
  var p = platform(n.userAgent || "", n.platform || "", n.maxTouchPoints || 0);
  if (p) w.location.replace(storeUrl(p, s));
})(window);
