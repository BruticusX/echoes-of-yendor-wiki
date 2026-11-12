/* Background music: the game's menu theme, looping seamlessly (Web Audio), with a toggle in the corner.
   Browsers only allow sound after the visitor interacts with the page, so it starts on the first click or key
   press, unless they turned it off before (remembered in this browser). */
(function () {
  "use strict";
  var VOLUME = 0.35;
  var KEY = "eoyMusic";
  function pref() { try { return localStorage.getItem(KEY) !== "off"; } catch (e) { return true; } }
  function setPref(on) { try { localStorage.setItem(KEY, on ? "on" : "off"); } catch (e) {} }

  var AC = window.AudioContext || window.webkitAudioContext;
  var ctx = null, gain = null, src = null, buffer = null, loading = null, playing = false;

  // the button
  var btn = document.createElement("button");
  btn.id = "musicBtn"; btn.className = "btn music-btn"; btn.type = "button";
  var NOTE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 17.5V5.2l11-2.2v12.3" fill="none" stroke="#3a2408" stroke-width="3.6" stroke-linejoin="round"/><path d="M9 17.5V5.2l11-2.2v12.3" fill="none" stroke="#f0c24a" stroke-width="2" stroke-linejoin="round"/><ellipse cx="6.4" cy="17.8" rx="3.1" ry="2.4" fill="#f0c24a" stroke="#3a2408" stroke-width="1"/><ellipse cx="17.4" cy="15.6" rx="3.1" ry="2.4" fill="#f0c24a" stroke="#3a2408" stroke-width="1"/></svg>';
  var SLASH = '<svg class="slash" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 3l18 18" stroke="#3a2408" stroke-width="4.4" stroke-linecap="round"/><path d="M3 3l18 18" stroke="#ff5a4a" stroke-width="2.4" stroke-linecap="round"/></svg>';
  btn.innerHTML = NOTE + SLASH;
  document.body.appendChild(btn);
  function render() {
    btn.classList.toggle("muted", !playing);
    var label = playing ? "Turn music off" : "Turn music on";
    btn.setAttribute("aria-label", label); btn.title = label;
    btn.setAttribute("aria-pressed", playing ? "true" : "false");
  }
  render();

  function audioBytes() {
    // the single-file preview carries the track inline; the real site loads it from audio/
    if (window.__AUDIO) {
      var bin = atob(window.__AUDIO), out = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
      return Promise.resolve(out.buffer);
    }
    var probe = document.createElement("audio");
    var ogg = probe.canPlayType && probe.canPlayType('audio/ogg; codecs="vorbis"');
    return fetch(ogg ? "audio/menu_theme.ogg" : "audio/menu_theme.mp3").then(function (r) { return r.arrayBuffer(); });
  }
  function load() {
    if (!loading) {
      loading = audioBytes().then(function (bytes) {
        return new Promise(function (res, rej) { ctx.decodeAudioData(bytes, res, rej); });
      }).then(function (b) { buffer = b; return b; });
    }
    return loading;
  }

  function start() {
    if (!AC) return;
    if (!ctx) { ctx = new AC(); gain = ctx.createGain(); gain.gain.value = 0; gain.connect(ctx.destination); }
    if (ctx.state === "suspended") ctx.resume();
    playing = true; render();
    load().then(function (b) {
      if (!playing || src) return;
      src = ctx.createBufferSource(); src.buffer = b; src.loop = true; src.connect(gain); src.start();
      var t = ctx.currentTime;
      gain.gain.cancelScheduledValues(t); gain.gain.setValueAtTime(gain.gain.value, t);
      gain.gain.linearRampToValueAtTime(VOLUME, t + 1.5); // fade in
    }).catch(function () { playing = false; render(); });
  }
  function stop() {
    playing = false; render();
    if (!ctx || !src) return;
    var s = src, t = ctx.currentTime;
    src = null;
    gain.gain.cancelScheduledValues(t); gain.gain.setValueAtTime(gain.gain.value, t);
    gain.gain.linearRampToValueAtTime(0, t + 0.6); // fade out
    setTimeout(function () { try { s.stop(); } catch (e) {} }, 700);
  }

  btn.addEventListener("click", function (e) {
    e.stopPropagation();
    if (playing) { stop(); setPref(false); } else { setPref(true); start(); }
  });
  // first interaction anywhere starts the music, if the visitor hasn't turned it off
  function firstTouch() {
    document.removeEventListener("pointerdown", firstTouch, true);
    document.removeEventListener("keydown", firstTouch, true);
    if (pref() && !playing) start();
  }
  document.addEventListener("pointerdown", firstTouch, true);
  document.addEventListener("keydown", firstTouch, true);
  // pause while the tab is hidden
  document.addEventListener("visibilitychange", function () {
    if (!ctx) return;
    if (document.hidden) ctx.suspend(); else if (playing) ctx.resume();
  });
})();
