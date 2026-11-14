// Tutor console: open-ticket list, chat, close ticket, and viewing a learner's shared screen.
(function () {
  var list = document.getElementById("tickets");
  var listStatus = document.getElementById("tickets-status");
  var chat = document.getElementById("chat");
  var heading = document.getElementById("chat-h");
  var log = document.getElementById("log");
  var form = document.getElementById("chat-form");
  var input = document.getElementById("message");
  var status = document.getElementById("status");
  var closeBtn = document.getElementById("close-ticket");
  var ETHIOPIC = /[ሀ-፿]/;
  var current = null, ws = null;
  var listeners = {};

  function emit(type, payload) { (listeners[type] || []).forEach(function (fn) { fn(payload); }); }

  function addMessage(m) {
    var p = document.createElement("p");
    if (m.role === "tutor") p.className = "mine";
    var who = document.createElement("span");
    who.className = "who";
    who.textContent = m.role === "tutor" ? "You (tutor)" : "Learner";
    var body = document.createElement("span");
    body.dir = "auto";
    if (ETHIOPIC.test(m.text)) body.lang = "am";
    body.textContent = m.text;
    p.appendChild(who);
    p.appendChild(body);
    log.appendChild(p);
    log.scrollTop = log.scrollHeight;
  }

  function renderTickets(tickets) {
    listStatus.textContent = tickets.length ? tickets.length + " open" : "No open tickets.";
    list.textContent = "";
    tickets.forEach(function (t) {
      var li = document.createElement("li");
      var b = document.createElement("button");
      b.type = "button";
      if (t.id === current) b.setAttribute("aria-current", "true");
      b.textContent = "Ticket " + t.id.slice(0, 6) + " · " + t.channel + " · " + t.lang;
      var small = document.createElement("small");
      small.dir = "auto";
      small.textContent = (t.last_message || t.topic || "No messages yet") + " (" + t.message_count + ")";
      b.appendChild(small);
      b.addEventListener("click", function () { openTicket(t.id); });
      li.appendChild(b);
      list.appendChild(li);
    });
  }

  function refresh() {
    fetch("/handoff/api/tickets", { credentials: "same-origin" })
      .then(function (r) { if (r.status === 401) { location.reload(); throw new Error("auth"); } return r.json(); })
      .then(function (d) { renderTickets(d.tickets); })
      .catch(function () { listStatus.textContent = "Could not load tickets."; });
  }

  function send(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) { ws.send(JSON.stringify(obj)); return true; }
    return false;
  }

  function openTicket(id) {
    if (ws) { ws.onclose = null; ws.close(); }
    emit("leave");
    current = id;
    chat.hidden = false;
    log.textContent = "";
    input.disabled = false;
    heading.textContent = "Ticket " + id.slice(0, 6);
    status.textContent = "Connecting…";
    var proto = location.protocol === "https:" ? "wss://" : "ws://";
    ws = new WebSocket(proto + location.host + "/handoff/ws/" + encodeURIComponent(id) + "?role=tutor");
    ws.onopen = function () { emit("open"); };
    ws.onmessage = function (e) {
      var m = JSON.parse(e.data);
      if (m.type === "history") { log.textContent = ""; m.messages.forEach(addMessage); }
      else if (m.type === "chat") addMessage(m);
      else if (m.type === "presence") status.textContent = m.learner ? "Learner is connected." : "Learner is not connected right now.";
      else if (m.type === "closed") { status.textContent = "Ticket closed."; input.disabled = true; refresh(); }
      emit(m.type, m);
    };
    ws.onclose = function () { if (current === id && !input.disabled) status.textContent = "Disconnected. Click the ticket to reconnect."; emit("leave"); };
    refresh();
    heading.focus();
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var text = input.value.trim();
    if (text && send({ type: "chat", text: text })) input.value = "";
    input.focus();
  });

  closeBtn.addEventListener("click", function () {
    if (!current || !window.confirm("Close this ticket? The learner will be told the chat has ended.")) return;
    fetch("/handoff/tickets/" + encodeURIComponent(current) + "/close", { method: "POST", credentials: "same-origin" })
      .then(refresh);
  });

  window.TutorConsole = {
    send: send,
    on: function (type, fn) { (listeners[type] = listeners[type] || []).push(fn); }
  };
  refresh();
  setInterval(refresh, 5000);
})();
