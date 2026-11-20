// Learner side of the voice call with the tutor, over WebRTC, signaled through the chat WebSocket.
// Rules, as for screen sharing: the call starts ONLY from the learner's click on "Talk by voice";
// nothing the tutor sends can turn on the learner's microphone. The learner can mute or end it, and it
// ends when the ticket closes or the page closes. The tutor is heard through this page.
(function () {
  var chat = window.HandoffChat;
  if (!chat) return;
  var S = chat.strings;
  var ICE = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };
  var mic = null, pc = null, pending = [], muted = false;

  function text(key, fallback) { return S[key] || fallback; }

  // The card, after the screen-sharing card (same look), built here so the template stays simple.
  var card = document.createElement("section");
  card.className = "share-feature-card voice-card";
  card.setAttribute("aria-labelledby", "voice-h");
  card.innerHTML =
    '<div class="share-card-layout">' +
    '  <div class="share-card-info">' +
    '    <div class="share-icon-box" aria-hidden="true">🎙️</div>' +
    '    <div class="share-text-block">' +
    '      <h2 id="voice-h"></h2>' +
    '      <p class="share-explain-text" id="voice-help"></p>' +
    '    </div>' +
    '  </div>' +
    '  <div class="voice-buttons">' +
    '    <button type="button" id="voice-start" class="btn-share-start" aria-describedby="voice-help"></button>' +
    '    <button type="button" id="voice-mute" class="btn-share-start" hidden aria-pressed="false"></button>' +
    '    <button type="button" id="voice-end" class="btn-share-start" hidden></button>' +
    '  </div>' +
    '</div>' +
    '<p id="voice-status" role="status" class="share-status-live"></p>' +
    '<audio id="voice-audio" autoplay></audio>';
  var anchor = document.getElementById("share-section") || document.querySelector(".chat-card");
  if (!anchor) return;
  anchor.parentNode.insertBefore(card, anchor.nextSibling);

  var startBtn = card.querySelector("#voice-start");
  var muteBtn = card.querySelector("#voice-mute");
  var endBtn = card.querySelector("#voice-end");
  var status = card.querySelector("#voice-status");
  var audio = card.querySelector("#voice-audio");
  card.querySelector("#voice-h").textContent = text("chat_voice_title", "Talk by voice");
  card.querySelector("#voice-help").textContent = text("chat_voice_explain",
    "Talk with the tutor using your microphone. Only you can start it, and you can mute or end it at any time.");
  startBtn.textContent = text("chat_voice_start", "Talk by voice");
  endBtn.textContent = text("chat_voice_end", "End voice call");

  function renderMute() {
    muteBtn.textContent = muted ? text("chat_voice_unmute", "Unmute my microphone") : text("chat_voice_mute", "Mute my microphone");
    muteBtn.setAttribute("aria-pressed", String(muted));
  }

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.RTCPeerConnection) {
    startBtn.disabled = true;
    status.textContent = text("chat_voice_unsupported", "Voice calls do not work in this browser. Please write your message.");
    return;
  }

  function signal(data) { data.channel = "voice"; chat.send({ type: "signal", data: data }); }

  function closePeer() {
    pending = [];
    if (pc) {
      try { pc.onicecandidate = null; pc.ontrack = null; pc.close(); } catch (e) {}
      pc = null;
    }
    audio.srcObject = null;
  }

  // (Re)send the learner's microphone to the tutor, and receive the tutor's. Only while the call is on.
  function offer() {
    if (!mic) return;
    closePeer();
    pc = new RTCPeerConnection(ICE);
    mic.getTracks().forEach(function (track) { pc.addTrack(track, mic); });
    pc.ontrack = function (e) {
      audio.srcObject = e.streams[0] || new MediaStream([e.track]);
      var p = audio.play();
      if (p && p.catch) p.catch(function () {});
    };
    pc.onicecandidate = function (e) { if (e.candidate) signal({ candidate: e.candidate }); };
    pc.createOffer()
      .then(function (o) { return pc.setLocalDescription(o); })
      .then(function () { signal({ description: pc.localDescription }); })
      .catch(function () {});
  }

  function end(message) {
    if (!mic) return;
    mic.getTracks().forEach(function (track) { track.stop(); });
    mic = null;
    closePeer();
    signal({ end: true });
    startBtn.hidden = false;
    muteBtn.hidden = endBtn.hidden = true;
    status.textContent = message || text("chat_voice_ended", "The voice call has ended.");
    startBtn.focus();
  }

  startBtn.addEventListener("click", function () {
    if (mic) return;
    status.textContent = "";
    navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
      .then(function (stream) {
        mic = stream;
        muted = false;
        renderMute();
        startBtn.hidden = true;
        muteBtn.hidden = endBtn.hidden = false;
        status.textContent = text("chat_voice_on", "Voice call on: the tutor can hear you.");
        offer();
        endBtn.focus();
      })
      .catch(function (err) {
        status.textContent = err && err.name === "NotAllowedError"
          ? text("chat_voice_denied", "The microphone is blocked. Allow it in your browser, or write your message.")
          : text("chat_voice_failed", "The microphone could not be started. Please write your message.");
      });
  });

  muteBtn.addEventListener("click", function () {
    if (!mic) return;
    muted = !muted;
    mic.getAudioTracks().forEach(function (track) { track.enabled = !muted; });
    renderMute();
    status.textContent = muted ? text("chat_voice_muted", "Your microphone is muted.") : text("chat_voice_on", "Voice call on: the tutor can hear you.");
  });

  endBtn.addEventListener("click", function () { end(); });

  chat.on("signal", function (m) {
    var d = m.data || {};
    if (d.channel !== "voice") return; // screen sharing has its own connection
    if (d.request === "offer") { offer(); return; } // the tutor (re)joined or turned on their microphone
    if (!pc) return;
    if (d.description && d.description.type === "answer") {
      pc.setRemoteDescription(d.description)
        .then(function () { while (pending.length) pc.addIceCandidate(pending.shift()).catch(function () {}); })
        .catch(function () {});
    } else if (d.candidate) {
      if (pc.remoteDescription) pc.addIceCandidate(d.candidate).catch(function () {});
      else pending.push(d.candidate);
    }
  });

  chat.on("open", function () { if (mic) offer(); });
  chat.on("closed", function () { end(); startBtn.disabled = true; });
  window.addEventListener("pagehide", function () { end(); });
})();
