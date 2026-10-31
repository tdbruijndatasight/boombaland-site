/* "Help develop Boombaland" form. A static site cannot receive posts, so the form sends to ONE configured endpoint.
   See GO_LIVE.md, step 7, for the two service options and how to switch. */
(function () {
  "use strict";

  // ---- CONFIG: the one place to change ----------------------------------------------------------------------------
  // provider: "web3forms" (default; needs ACCESS_KEY) or "formspree" (ENDPOINT = https://formspree.io/f/<form id>).
  var IDEA_FORM = {
    provider: "web3forms",
    endpoint: "https://api.web3forms.com/submit",
    accessKey: ""            // TODO at go-live: the Web3Forms access key mailed to support@boombaland.com
  };
  // On this machine (stage 1) every submission goes to the local receiver instead: tools/idea_receiver.py on :8767.
  var LOCAL = /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
  if (LOCAL) IDEA_FORM = { provider: "local", endpoint: "http://127.0.0.1:8767/submit", accessKey: "" };
  // -------------------------------------------------------------------------------------------------------------------

  var form = document.getElementById("idea-form");
  if (!form) return;
  var err = document.getElementById("idea-error"), done = document.getElementById("idea-done");
  var btn = form.querySelector("button[type=submit]");

  function v(id) { return document.getElementById(id); }
  function fail(msg, field) { err.textContent = msg; err.hidden = false; if (field) field.focus(); }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    err.hidden = true;
    var title = v("idea-title").value.trim(), idea = v("idea-text").value.trim();
    var name = v("idea-name").value.trim(), email = v("idea-email").value.trim();
    var age16 = v("idea-age").checked, consent = v("idea-consent").checked;
    if (!title) return fail("Please give your idea a title.", v("idea-title"));
    if (!idea) return fail("Please describe your idea.", v("idea-text"));
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return fail("That email address doesn't look right.", v("idea-email"));
    if ((name || email) && !age16)
      return fail("To send your name or email, tick \"I am 16 or older\". Younger? Leave name and email empty.", v("idea-age"));
    if (!consent) return fail("Please tick the box to agree, so we can look at your idea.", v("idea-consent"));
    if (!IDEA_FORM.endpoint || (IDEA_FORM.provider === "web3forms" && !IDEA_FORM.accessKey))
      return fail("The idea form is not switched on yet. Please mail your idea to support@boombaland.com.");

    var data = {
      title: title, idea: idea, name: (age16 ? name : ""), email: (age16 ? email : ""),
      age16: age16 ? "yes" : "no", consent: "yes", page: location.pathname
    };
    var hp = v("idea-hp").value;
    if (IDEA_FORM.provider === "web3forms") {
      data.access_key = IDEA_FORM.accessKey;
      data.subject = "Boombaland idea: " + title;
      data.from_name = "Boombaland website";
      data.botcheck = hp;
      if (!data.email) delete data.email;
    } else if (IDEA_FORM.provider === "formspree") {
      data._subject = "Boombaland idea: " + title;
      data._gotcha = hp;
      if (data.email) data._replyto = data.email;
    } else {
      data.botcheck = hp;
    }
    btn.disabled = true;
    fetch(IDEA_FORM.endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify(data)
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, j: j }; });
    }).then(function (res) {
      btn.disabled = false;
      if (!res.ok || res.j.success === false) throw new Error((res.j && res.j.message) || "failed");
      form.reset();
      done.hidden = false;
      done.focus && done.setAttribute("tabindex", "-1");
      done.focus();
    }).catch(function () {
      btn.disabled = false;
      fail("Sorry, your idea could not be sent. Please try again later, or mail it to support@boombaland.com.");
    });
  });
})();
