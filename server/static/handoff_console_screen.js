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
    var pc = null, pendingCandidates = [], fallbackTimer = null;

    function signal(data) { tutor.send({ type: "signal", data: data }); }

    function drainCandidates() {
      while (pendingCandidates.length && pc && pc.remoteDescription) {
        pc.addIceCandidate(pendingCandidates.shift()).catch(function () {});
      }
    }

    function teardown() {
      clearTimeout(fallbackTimer);
      pendingCandidates = [];
      if (pc) {
        try {
          pc.onicecandidate = null;
          pc.ontrack = null;
          pc.close();
        } catch (e) {}
        pc = null;
      }
      if (video) {
        video.pause();
        video.srcObject = null;
      }
      if (box) box.hidden = true;
    }

    function onOffer(description) {
      clearTimeout(fallbackTimer);
      if (pc) {
        try {
          pc.onicecandidate = null;
          pc.ontrack = null;
          pc.close();
        } catch (e) {}
        pc = null;
      }
      pendingCandidates = [];
      pc = new RTCPeerConnection(ICE);
      var mine = pc;

      pc.ontrack = function (e) {
        if (box) box.hidden = false;
        if (video) {
          var stream = e.streams[0] || new MediaStream([e.track]);
          video.srcObject = stream;
          video.muted = true;
          video.playsInline = true;
          var doPlay = function () {
            var p = video.play();
            if (p && p.catch) p.catch(function () {});
          };
          video.onloadedmetadata = doPlay;
          if (e.track) e.track.onunmute = doPlay;
          doPlay();
        }
      };

      pc.onicecandidate = function (e) {
        if (e.candidate) signal({ candidate: e.candidate });
      };

      mine.setRemoteDescription(description)
        .then(function () { return mine.createAnswer(); })
        .then(function (a) { return mine.setLocalDescription(a); })
        .then(function () {
          signal({ description: mine.localDescription });
          drainCandidates();
        })
        .catch(function () {});
    }

    // A call already in progress reaches a tutor who (re)joins
    tutor.on("open", function () { signal({ request: "offer" }); });

    tutor.on("signal", function (m) {
      var d = m.data || {};
      if (d.channel === "voice") return; // the voice call has its own connection (handoff_console_voice.js)
      if (d.description && d.description.type === "offer") {
        onOffer(d.description);
      } else if (d.candidate) {
        if (pc && pc.remoteDescription) {
          pc.addIceCandidate(d.candidate).catch(function () {});
        } else {
          pendingCandidates.push(d.candidate);
        }
      }
    });

    tutor.on("share", function (m) {
      if (m.state === "stopped") {
        teardown();
      } else if (m.state === "started") {
        if (box) box.hidden = false;
        // The learner immediately sends an offer right after announcing "started".
        // Do not immediately request offer to avoid double-offer collisions; request only as a fallback.
        clearTimeout(fallbackTimer);
        fallbackTimer = setTimeout(function () {
          if (!pc || !pc.remoteDescription) {
            signal({ request: "offer" });
          }
        }, 1500);
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
