/* The animated title logo from the game's TitleScene: two purple flames (effects/Fireball, 24 frames at 12fps,
   the second flipped and half a cycle ahead) in gold braziers on the gem ornaments either side of "ECHOES OF", and the glow layer
   that fades in and out with light blending: brightness = max(0, sin t), restarting every 1.5 pi seconds. */
(function () {
  "use strict";
  function src(p) { return (window.__IMG && window.__IMG[p]) || p; }
  var FRAME = 47, COLS = 5, FRAMES = 24, FPS = 12;   // calmer flicker, as in the game
  var sheet = new Image(); sheet.src = src("img/ui/fireball.png");
  var running = null;

  function mount(root) {
    if (running) running.stop();
    var logo = root.querySelector(".logo-img"), glow = root.querySelector(".logo-glow");
    var flames = [].slice.call(root.querySelectorAll("canvas.flame"));
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var t = 0, last = performance.now(), alive = true;
    flames.forEach(function (c) { c.width = FRAME; c.height = FRAME; });

    function draw(now) {
      if (!alive) return;
      var dt = Math.min(0.1, (now - last) / 1000); last = now;
      if (!reduce) t += dt;
      var f = Math.floor(t * FPS);
      flames.forEach(function (c, i) {
        var ctx = c.getContext("2d");
        ctx.imageSmoothingEnabled = false;
        ctx.clearRect(0, 0, FRAME, FRAME);
        if (!sheet.complete || !sheet.naturalWidth) return;
        var k = (f + (i ? 12 : 0)) % FRAMES; // second flame: offset by half the animation
        ctx.drawImage(sheet, (k % COLS) * FRAME, Math.floor(k / COLS) * FRAME, FRAME, FRAME, 0, 0, FRAME, FRAME);
      });
      var gt = t % (1.5 * Math.PI);
      glow.style.opacity = reduce ? 0.6 : Math.max(0, Math.sin(gt)).toFixed(3);
      if (document.contains(root)) requestAnimationFrame(draw); else alive = false;
    }
    requestAnimationFrame(draw);
    running = { stop: function () { alive = false; } };
  }
  window.EOYLogo = { mount: mount };
})();
