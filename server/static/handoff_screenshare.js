// Learner-controlled screen sharing over WebRTC, signaled through the chat WebSocket.
// Rules: sharing starts ONLY from the learner's click on "Share my screen". Nothing the tutor
// sends can start it. It stops from our Stop button, the browser's own stop control, the ticket
// closing, or the page closing.
(function () {
  var chat = window.HandoffChat;
  if (!chat) return;
  var S = chat.strings;
  var section = document.getElementById("share-section");
  var startBtn = document.getElementById("share-start");
  var stopBtn = document.getElementById("share-stop");
  var banner = document.getElementById("share-banner");
  var status = document.getElementById("share-status");
  var ICE = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };
  var stream = null, pc = null, pendingCandidates = [];

  section.hidden = false;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia || !window.RTCPeerConnection) {
    startBtn.disabled = true;
    status.textContent = S.share_unsupported;
    return;
  }

  function signal(data) { chat.send({ type: "signal", data: data }); }

  function closePeer() {
    pendingCandidates = [];
    if (pc) {
      try {
        pc.onicecandidate = null;
        pc.close();
      } catch (e) {}
      pc = null;
    }
  }

  function drainCandidates() {
    while (pendingCandidates.length && pc && pc.remoteDescription) {
      pc.addIceCandidate(pendingCandidates.shift()).catch(function () {});
    }
  }

  // (Re)send the current stream to the tutor. Only ever called while the learner is sharing.
  function offer() {
    if (!stream) return;
    closePeer();
    pc = new RTCPeerConnection(ICE);
    stream.getTracks().forEach(function (track) { pc.addTrack(track, stream); });
    pc.onicecandidate = function (e) { if (e.candidate) signal({ candidate: e.candidate }); };
    pc.createOffer()
      .then(function (o) { return pc.setLocalDescription(o); })
      .then(function () { signal({ description: pc.localDescription }); })
      .catch(function () {});
  }

  function stop(message) {
    if (!stream) return;
    stream.getTracks().forEach(function (track) { track.onended = null; track.stop(); });
    stream = null;
    closePeer();
    chat.send({ type: "share", state: "stopped" });
    banner.hidden = true;
    startBtn.disabled = false;
    status.textContent = message || S.share_stopped;
    startBtn.focus();
  }

  startBtn.addEventListener("click", function () {
    if (stream) return;
    status.textContent = "";
    navigator.mediaDevices.getDisplayMedia({ video: true, audio: false })
      .then(function (s) {
        stream = s;
        // Fires when the learner uses the browser's own "Stop sharing" control.
        var videoTrack = s.getVideoTracks()[0];
        if (videoTrack) {
          videoTrack.onended = function () { stop(); };
        }
        banner.hidden = false;
        startBtn.disabled = true;
        chat.send({ type: "share", state: "started" });
        offer();
        stopBtn.focus();
      })
      .catch(function (err) {
        // NotAllowedError = the learner pressed Cancel: not an error worth announcing loudly.
        status.textContent = err && err.name === "NotAllowedError" ? S.share_stopped : S.share_failed;
      });
  });

  stopBtn.addEventListener("click", function () { stop(); });

  chat.on("signal", function (m) {
    var d = m.data || {};
    if (d.channel === "voice") return; // the voice call has its own connection (handoff_voice.js)
    if (d.request === "offer") {
      // Do not recreate peer connection if we just offered or are already connected
      if (pc && (pc.signalingState === "have-local-offer" || pc.connectionState === "connected" || pc.iceConnectionState === "connected")) {
        return;
      }
      offer();
      return;
    } // tutor (re)joined: no-op unless already sharing
    if (!pc) return;
    if (d.description && d.description.type === "answer") {
      pc.setRemoteDescription(d.description)
        .then(drainCandidates)
        .catch(function () {});
    } else if (d.candidate) {
      if (pc.remoteDescription) {
        pc.addIceCandidate(d.candidate).catch(function () {});
      } else {
        pendingCandidates.push(d.candidate);
      }
    }
  });

  chat.on("open", function () { if (stream) { chat.send({ type: "share", state: "started" }); offer(); } });
  chat.on("closed", function () { stop(); startBtn.disabled = true; });
  window.addEventListener("pagehide", function () { stop(); });
})();
