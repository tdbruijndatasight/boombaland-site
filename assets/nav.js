/* Phone menu: the top-bar menu button opens the main nav as a panel under the bar. Desktop shows the nav inline and
   ignores all of this (CSS). Esc or a click outside closes it; focus moves into the panel and back to the button. */
(function () {
  "use strict";
  var btn = document.querySelector(".menu-btn");
  var navEl = document.getElementById("site-nav");
  if (!btn || !navEl) return;
  var bar = btn.closest(".topbar");
  var icon = btn.querySelector("img");
  var phone = window.matchMedia("(max-width: 799px)");

  function setOpen(open, returnFocus) {
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    bar.classList.toggle("menu-open", open);
    icon.src = open ? "/assets/img/menu-pressed-96.png" : "/assets/img/menu-96.png";
    if (open) {
      var first = navEl.querySelector("a");
      if (first) first.focus();
    } else if (returnFocus) {
      btn.focus();
    }
  }
  function isOpen() { return btn.getAttribute("aria-expanded") === "true"; }

  btn.addEventListener("click", function () { setOpen(!isOpen(), true); });
  document.addEventListener("keydown", function (e) {
    if ((e.key === "Escape" || e.key === "Esc") && isOpen()) { e.preventDefault(); setOpen(false, true); }
  });
  document.addEventListener("click", function (e) {
    if (isOpen() && !bar.contains(e.target)) setOpen(false, false);
  });
  // Tabbing past the last link closes the panel (focus has already left, so leave it where it went).
  navEl.addEventListener("focusout", function (e) {
    if (isOpen() && phone.matches && e.relatedTarget && !bar.contains(e.relatedTarget)) setOpen(false, false);
  });
  // Going to desktop width resets the state so the inline nav never inherits an open panel.
  var reset = function () { if (!phone.matches && isOpen()) setOpen(false, false); };
  if (phone.addEventListener) phone.addEventListener("change", reset); else if (phone.addListener) phone.addListener(reset);
})();
