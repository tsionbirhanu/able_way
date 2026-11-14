// SMS simulator: sends to the real webhook and polls the outbox for alerts.
(function () {
  var log = document.getElementById("log");
  var form = document.getElementById("form");
  var text = document.getElementById("text");
  var from = document.getElementById("from");
  var status = document.getElementById("status");
  var lastOutboxId = 0;
  var hasAmharic = /[ሀ-፿]/;

  function add(kind, body, label) {
    var p = document.createElement("p");
    p.className = "msg " + kind;
    p.dir = "auto";
    if (hasAmharic.test(body)) p.lang = "am";
    var small = document.createElement("small");
    small.textContent = label + " · " + body.length + " chars";
    p.appendChild(document.createTextNode(body));
    p.appendChild(small);
    log.appendChild(p);
    log.scrollTop = log.scrollHeight;
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var body = text.value.trim();
    if (!body) return;
    add("out", body, "You");
    text.value = "";
    fetch("/sms/inbound", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from: from.value.trim(), text: body })
    })
      .then(function (r) { return r.json(); })
      .then(function (d) { add("in", d.reply || d.error || "(no reply)", "Reply"); status.textContent = ""; })
      .catch(function () { status.textContent = "Could not reach the server."; });
  });

  function poll() {
    var number = from.value.trim();
    if (!number) return;
    fetch("/sms/outbox?to=" + encodeURIComponent(number) + "&after=" + lastOutboxId)
      .then(function (r) { return r.json(); })
      .then(function (d) {
        (d.messages || []).forEach(function (m) {
          lastOutboxId = Math.max(lastOutboxId, m.id);
          add("alert", m.text, "Alert");
        });
      })
      .catch(function () {});
  }
  from.addEventListener("change", function () { lastOutboxId = 0; log.textContent = ""; poll(); });
  poll();
  setInterval(poll, 4000);
})();
