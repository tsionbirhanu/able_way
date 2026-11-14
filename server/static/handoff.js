/* Human handoff hook for the web widget.
 *
 *   <script src="http://localhost:8000/handoff/static/handoff.js"></script>
 *   <button onclick="AssistantHandoff.open()">Talk to a person</button>
 *
 * AssistantHandoff.open({lang: "am", topic: "last question the learner asked"})
 * creates a ticket and opens the live chat page in a new tab. Returns a Promise of the ticket id.
 * The server address is taken from this script's own URL, so it also works from file:// pages.
 */
(function () {
  var script = document.currentScript;
  var base = "";
  try { base = new URL(script.src).origin; } catch (e) { base = ""; }

  function open(options) {
    options = options || {};
    var lang = options.lang || document.documentElement.lang || "en";
    lang = String(lang).toLowerCase().indexOf("am") === 0 ? "am" : "en";
    // Open the tab now, inside the click, so popup blockers allow it.
    var tab = window.open("about:blank", "_blank");
    var fallback = base + "/handoff/start?lang=" + lang;
    // No Content-Type header on purpose: keeps this a "simple" request (no CORS preflight).
    return fetch(base + "/handoff/tickets", {
      method: "POST",
      body: JSON.stringify({ lang: lang, topic: options.topic || "", channel: options.channel || "web" })
    })
      .then(function (r) { if (!r.ok) throw new Error("ticket failed"); return r.json(); })
      .then(function (d) {
        var url = base + d.chat_url;
        if (tab) tab.location = url; else window.location.assign(url);
        return d.ticket_id;
      })
      .catch(function (err) {
        if (tab) tab.location = fallback; else window.location.assign(fallback);
        throw err;
      });
  }

  window.AssistantHandoff = { open: open, baseUrl: base };
})();
