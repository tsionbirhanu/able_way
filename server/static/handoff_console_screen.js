// Tutor side of screen sharing: view only. The tutor never starts a share; it can only ask the
// learner's page to re-send a stream the learner has already chosen to share.
(function () {
  function attach() {
    var tutor = window.TutorConsole;
    if (!tutor || !window.RTCPeerConnection || window.__tutorScreenAttached) return;
    window.__tutorScreenAttached = true;

    var box = document.getElementById("screen");
    var video = document.getElementById("screen-video");
    if (!box || !video) return;
    var ICE = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };
    var pc = null, queue = Promise.resolve();

    function signal(data) { tutor.send({ type: "signal", data: data }); }

    function teardown() {
      if (pc) {
        try { pc.close(); } catch (e) {}
        pc = null;
      }
      if (video) video.srcObject = null;
      if (box) box.hidden = true;
      queue = Promise.resolve();
    }

    function onOffer(description) {
      if (pc) {
        try { pc.close(); } catch (e) {}
      }
      pc = new RTCPeerConnection(ICE);
      var mine = pc;
      pc.ontrack = function (e) {
        if (video) {
          video.srcObject = e.streams[0] || new MediaStream([e.track]);
          var p = video.play();
          if (p && p.catch) p.catch(function () {});
        }
        if (box) box.hidden = false;
      };
      pc.onicecandidate = function (e) { if (e.candidate) signal({ candidate: e.candidate }); };
      queue = mine.setRemoteDescription(description)
        .then(function () { return mine.createAnswer(); })
        .then(function (a) { return mine.setLocalDescription(a); })
        .then(function () { signal({ description: mine.localDescription }); })
        .catch(function () {});
    }

    tutor.on("open", function () { signal({ request: "offer" }); });
    // (The voice call re-asks for its own offer: handoff_console_voice.js.)
    tutor.on("signal", function (m) {
      var d = m.data || {};
      if (d.channel === "voice") return; // the voice call has its own connection (handoff_console_voice.js)
      if (d.description && d.description.type === "offer") {
        onOffer(d.description);
      } else if (d.candidate && pc) {
        var mine = pc;
        queue = queue.then(function () { return mine.addIceCandidate(d.candidate); }).catch(function () {});
      }
    });
    tutor.on("share", function (m) {
      if (m.state === "stopped") {
        teardown();
      } else if (m.state === "started") {
        signal({ request: "offer" });
      }
    });
    tutor.on("closed", teardown);
    tutor.on("leave", teardown);
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
