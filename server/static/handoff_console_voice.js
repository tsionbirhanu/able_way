// Tutor side of the voice call. The learner starts it ("Talk by voice"); the tutor then hears the
// learner here, and can turn on their own microphone to answer by voice. The tutor can never turn on
// the learner's microphone. Turning the tutor's microphone on or off asks the learner's page for a new
// offer, so the call is set up again with or without the tutor's voice.
(function () {
  function attach() {
    var tutor = window.TutorConsole;
    if (!tutor || !window.RTCPeerConnection || window.__tutorVoiceAttached) return;
    var anchor = document.getElementById("chat-log");
    if (!anchor) return;
    window.__tutorVoiceAttached = true;

    var ICE = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };
    var pc = null, queue = Promise.resolve(), myMic = null, inCall = false;

    // The voice bar, above the conversation.
    var bar = document.createElement("div");
    bar.className = "voice-call-bar";
    bar.setAttribute("role", "region");
    bar.setAttribute("aria-label", "Voice call with the learner");
    bar.style.cssText = "display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:8px 12px;" +
      "border-bottom:1px solid #d0d7de;background:#f0f7ff;color:#0b2545;font-size:0.95rem";
    bar.innerHTML =
      '<span id="voice-state" role="status">🎙️ No voice call</span>' +
      '<button type="button" id="voice-mic" style="min-height:40px;padding:6px 12px;border-radius:8px;border:2px solid #0b2545;background:#fff;color:#0b2545;font-weight:700;cursor:pointer">🎤 Turn on my microphone</button>' +
      '<audio id="voice-learner" autoplay controls aria-label="The learner\'s voice" style="height:32px;max-width:240px"></audio>';
    anchor.parentNode.insertBefore(bar, anchor);
    var state = bar.querySelector("#voice-state");
    var micBtn = bar.querySelector("#voice-mic");
    var audio = bar.querySelector("#voice-learner");

    function signal(data) { data.channel = "voice"; tutor.send({ type: "signal", data: data }); }

    function renderMic() {
      micBtn.textContent = myMic ? "🔇 Turn off my microphone" : "🎤 Turn on my microphone";
      micBtn.setAttribute("aria-pressed", String(!!myMic));
    }

    function teardown(message) {
      if (pc) {
        try { pc.close(); } catch (e) {}
        pc = null;
      }
      audio.srcObject = null;
      queue = Promise.resolve();
      inCall = false;
      if (message) state.textContent = message;
    }

    function onOffer(description) {
      if (pc) {
        try { pc.close(); } catch (e) {}
      }
      pc = new RTCPeerConnection(ICE);
      var mine = pc;
      if (myMic) myMic.getTracks().forEach(function (track) { mine.addTrack(track, myMic); });
      pc.ontrack = function (e) {
        audio.srcObject = e.streams[0] || new MediaStream([e.track]);
        var p = audio.play();
        if (p && p.catch) p.catch(function () {});
      };
      pc.onicecandidate = function (e) { if (e.candidate) signal({ candidate: e.candidate }); };
      inCall = true;
      state.textContent = myMic
        ? "🎙️ Voice call on"
        : "🎙️ You can hear the learner";
      queue = mine.setRemoteDescription(description)
        .then(function () { return mine.createAnswer(); })
        .then(function (a) { return mine.setLocalDescription(a); })
        .then(function () { signal({ description: mine.localDescription }); })
        .catch(function () {});
    }

    micBtn.addEventListener("click", function () {
      if (myMic) {
        myMic.getTracks().forEach(function (track) { track.stop(); });
        myMic = null;
        renderMic();
        if (inCall) signal({ request: "offer" }); // set the call up again without the tutor's voice
        return;
      }
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        state.textContent = "This browser cannot use a microphone.";
        return;
      }
      navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
        .then(function (stream) {
          myMic = stream;
          renderMic();
          if (inCall) signal({ request: "offer" }); // the learner's page sends a new offer; we answer with our voice
          else state.textContent = "🎤 Microphone ready";
        })
        .catch(function () { state.textContent = "Microphone blocked: allow it in the address bar"; });
    });

    tutor.on("open", function () { signal({ request: "offer" }); }); // a call already on reaches a tutor who (re)joins
    tutor.on("signal", function (m) {
      var d = m.data || {};
      if (d.channel !== "voice") return; // screen sharing has its own connection
      if (d.end) { teardown("🎙️ Voice call ended"); return; }
      if (d.description && d.description.type === "offer") {
        onOffer(d.description);
      } else if (d.candidate && pc) {
        var mine = pc;
        queue = queue.then(function () { return mine.addIceCandidate(d.candidate); }).catch(function () {});
      }
    });
    tutor.on("closed", function () { teardown("🎙️ No voice call"); });
    tutor.on("leave", function () { teardown("🎙️ No voice call"); });
    renderMic();
  }

  if (window.TutorConsole) {
    attach();
  } else {
    document.addEventListener("DOMContentLoaded", attach);
    window.addEventListener("load", attach);
    var tries = 0;
    var t = setInterval(function () {
      tries++;
      if (window.TutorConsole || tries > 30) {
        clearInterval(t);
        attach();
      }
    }, 100);
  }
})();
