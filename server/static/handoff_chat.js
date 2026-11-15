// Learner side of the live chat. Screen sharing lives in handoff_screenshare.js.
(function () {
  var config = JSON.parse(document.getElementById("handoff-config").textContent);
  var S = config.strings;
  var log = document.getElementById("log");
  var form = document.getElementById("chat-form");
  var input = document.getElementById("message");
  var status = document.getElementById("status");
  var ETHIOPIC = /[ሀ-፿]/;
  var ws = null, closed = false, retry = null;
  var listeners = {};

  function emit(type, payload) { (listeners[type] || []).forEach(function (fn) { fn(payload); }); }

  function addMessage(m) {
    var p = document.createElement("p");
    if (m.role === "learner") p.className = "mine";
    var who = document.createElement("span");
    who.className = "who";
    who.textContent = m.role === "learner" ? S.chat_you : m.role === "mimi" ? "Mimi" : S.chat_tutor;
    var body = document.createElement("span");
    body.dir = "auto"; // right-to-left text (Arabic...) displays correctly
    if (ETHIOPIC.test(m.text)) body.lang = "am";
    body.textContent = m.text;
    p.appendChild(who);
    p.appendChild(body);
    log.appendChild(p);
    log.scrollTop = log.scrollHeight;
  }

  function setClosed() {
    closed = true;
    status.textContent = S.chat_closed;
    input.disabled = true;
    form.querySelector("button").disabled = true;
    emit("closed");
  }

  function send(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) { ws.send(JSON.stringify(obj)); return true; }
    return false;
  }

  function connect() {
    var proto = location.protocol === "https:" ? "wss://" : "ws://";
    ws = new WebSocket(proto + location.host + "/handoff/ws/" + encodeURIComponent(config.ticketId) + "?role=learner");
    ws.onopen = function () { status.textContent = S.chat_connected_waiting; emit("open"); };
    ws.onmessage = function (e) {
      var m = JSON.parse(e.data);
      if (m.type === "history") { log.textContent = ""; m.messages.forEach(addMessage); }
      else if (m.type === "chat") addMessage(m);
      else if (m.type === "presence") { if (!closed) status.textContent = m.tutor ? S.chat_tutor_here : S.chat_connected_waiting; }
      else if (m.type === "closed") setClosed();
      emit(m.type, m);
    };
    ws.onclose = function (e) {
      emit("disconnected");
      if (closed || e.code === 4404) { if (!closed) setClosed(); return; }
      status.textContent = S.chat_disconnected;
      clearTimeout(retry);
      retry = setTimeout(connect, 2000);
    };
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var text = input.value.trim();
    if (!text) return;
    if (send({ type: "chat", text: text })) input.value = "";
    input.focus();
  });

  window.HandoffChat = {
    send: send,
    strings: S,
    on: function (type, fn) { (listeners[type] = listeners[type] || []).push(fn); }
  };
  connect();

  // Screen sharing is optional: load it after the chat works.
  var extra = document.createElement("script");
  extra.src = "/handoff/static/handoff_screenshare.js";
  extra.onerror = function () {};
  document.body.appendChild(extra);
})();
