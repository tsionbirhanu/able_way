// Tutor side of screen sharing: view only. The tutor never starts a share; it can only ask the
// learner's page to re-send a stream the learner has already chosen to share.
(function () {
  var tutor = window.TutorConsole;
  if (!tutor || !window.RTCPeerConnection) return;
  var box = document.getElementById("screen");
  var video = document.getElementById("screen-video");
  var ICE = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };
  var pc = null, queue = Promise.resolve();

  function signal(data) { tutor.send({ type: "signal", data: data }); }

  function teardown() {
    if (pc) { pc.close(); pc = null; }
    video.srcObject = null;
    box.hidden = true;
    queue = Promise.resolve();
  }

  function onOffer(description) {
    if (pc) pc.close();
    pc = new RTCPeerConnection(ICE);
    var mine = pc;
    pc.ontrack = function (e) {
      video.srcObject = e.streams[0] || new MediaStream([e.track]);
      box.hidden = false;
      var p = video.play();
      if (p && p.catch) p.catch(function () {});
    };
    pc.onicecandidate = function (e) { if (e.candidate) signal({ candidate: e.candidate }); };
    queue = mine.setRemoteDescription(description)
      .then(function () { return mine.createAnswer(); })
      .then(function (a) { return mine.setLocalDescription(a); })
      .then(function () { signal({ description: mine.localDescription }); })
      .catch(function () {});
  }

  tutor.on("open", function () { signal({ request: "offer" }); });
  tutor.on("signal", function (m) {
    var d = m.data || {};
    if (d.description && d.description.type === "offer") onOffer(d.description);
    else if (d.candidate && pc) {
      var mine = pc;
      queue = queue.then(function () { return mine.addIceCandidate(d.candidate); }).catch(function () {});
    }
  });
  tutor.on("share", function (m) { if (m.state === "stopped") teardown(); });
  tutor.on("closed", teardown);
  tutor.on("leave", teardown);
})();
