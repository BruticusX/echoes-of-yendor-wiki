/* The game's title-screen background (ui/TitleBackground.java), ported to a canvas:
   a painted dungeon shaft that slowly drifts and breathes, two layers of mist rolling across it,
   a violet glow pulsing up from the depths and embers flickering along the bottom edge. */
(function () {
  "use strict";
  var canvas = document.createElement("canvas");
  canvas.id = "titleBg";
  canvas.setAttribute("aria-hidden", "true");
  document.body.insertBefore(canvas, document.body.firstChild);
  var ctx = canvas.getContext("2d");

  function src(p) { return (window.__IMG && window.__IMG[p]) || p; }
  function load(p) { var i = new Image(); i.src = src(p); return i; }
  var bg = load("img/ui/title_bg.png"), fog = load("img/ui/title_fog.png"), glow = load("img/ui/title_glow.png");

  var W = 0, H = 0, dpr = 1, zoom = 3, gw = 0, gh = 0; // gw/gh: screen size in game pixels
  var time = 0;
  try { time = parseFloat(sessionStorage.getItem("eoyBgTime")) || 0; } catch (e) {} // keep the drift between pages
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth; H = window.innerHeight;
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    canvas.style.width = W + "px"; canvas.style.height = H + "px";
    // the game draws at a whole-number zoom of about 3x on phones; match that feel
    zoom = Math.max(2, Math.min(4, Math.round(Math.min(W, H) / 220)));
    gw = W / zoom; gh = H / zoom;
  }
  window.addEventListener("resize", resize);
  resize();

  // ---- embers: FlameParticle (0xEE7722, 0.6s life, size 4 shrinking, accel -80, fade in over the first 20%)
  var embers = [], pourTimer = 0;
  function emit() { embers.push({ x: Math.random() * gw, y: gh, vy: 0, left: 0.6 }); }

  function drawImg(img, x, y, s, alpha, flip) {
    if (!img.complete || !img.naturalWidth) return;
    ctx.globalAlpha = alpha;
    var k = zoom * dpr;
    if (flip) {
      ctx.save();
      ctx.translate((x + img.naturalWidth * s) * k, y * k);
      ctx.scale(-1, 1);
      ctx.drawImage(img, 0, 0, img.naturalWidth * s * k, img.naturalHeight * s * k);
      ctx.restore();
    } else {
      ctx.drawImage(img, x * k, y * k, img.naturalWidth * s * k, img.naturalHeight * s * k);
    }
  }

  function layFog(speed, cy, sizeMult, alpha, flip) {
    if (!fog.naturalWidth) return;
    var s = gw * sizeMult / fog.naturalWidth, w = fog.naturalWidth * s, h = fog.naturalHeight * s;
    var off = (time * speed) % w; if (off < 0) off += w;
    for (var i = 0; i < 2; i++) drawImg(fog, -off + i * w - (w - gw) / 2, cy - h / 2, s, alpha, flip);
  }

  var last = performance.now();
  function frame(now) {
    var dt = Math.min(0.1, (now - last) / 1000); last = now;
    if (!reduce) time += dt;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.imageSmoothingEnabled = false;
    ctx.globalCompositeOperation = "source-over";
    ctx.globalAlpha = 1;
    ctx.fillStyle = "#0b0912";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (bg.naturalWidth) {
      // cover the screen with a little room to drift, slow ping-pong drift and a gentle breathing zoom
      var base = Math.max(gw / bg.naturalWidth, gh / bg.naturalHeight) * 1.12;
      var sc = base * (1 + 0.025 * Math.sin(time * 0.11));
      var bw = bg.naturalWidth * sc, bh = bg.naturalHeight * sc;
      var bx = -(bw - gw) * (0.5 + 0.5 * Math.sin(time * 0.07));
      var by = -(bh - gh) * (0.5 + 0.5 * Math.sin(time * 0.045 + 1));
      drawImg(bg, bx, by, sc, 1);

      // violet glow over the bottom of the shaft, pulsing (additive, like Blending.setLightMode)
      if (glow.naturalWidth) {
        var gs = Math.max(gw, gh) * 0.55 / glow.naturalWidth;
        ctx.globalCompositeOperation = "lighter";
        drawImg(glow, bx + bw * 0.47 - glow.naturalWidth * gs / 2, by + bh * 0.88 - glow.naturalHeight * gs / 2, gs,
          0.35 + 0.25 * Math.sin(time * 1.3));
        ctx.globalCompositeOperation = "source-over";
      }
    }
    layFog(6, gh * 0.25, 1.6, 0.35, false);
    layFog(-11, gh * 0.62, 2.2, 0.45, true);

    // embers
    if (!reduce) {
      pourTimer += dt;
      var interval = 0.12 * Math.max(1, 360 / gw); // same density per screen width as the phone version
      while (pourTimer >= interval) { pourTimer -= interval; emit(); }
    }
    ctx.globalCompositeOperation = "lighter";
    ctx.fillStyle = "#ee7722";
    var k = zoom * dpr;
    for (var i = embers.length - 1; i >= 0; i--) {
      var p = embers[i];
      p.left -= dt; if (p.left <= 0) { embers.splice(i, 1); continue; }
      p.vy -= 80 * dt; p.y += p.vy * dt;
      var f = p.left / 0.6, size = 4 * f;
      ctx.globalAlpha = f > 0.8 ? (1 - f) * 5 : 1;
      ctx.fillRect((p.x - size / 2) * k, (p.y - size / 2) * k, size * k, size * k);
    }
    ctx.globalCompositeOperation = "source-over";

    // the darkness gradient: darker at the top and bottom
    ctx.globalAlpha = 1;
    var g = ctx.createLinearGradient(0, 0, 0, canvas.height);
    g.addColorStop(0, "rgba(0,0,0,.53)"); g.addColorStop(0.2, "rgba(0,0,0,.13)"); g.addColorStop(0.4, "rgba(0,0,0,0)");
    g.addColorStop(0.6, "rgba(0,0,0,0)"); g.addColorStop(0.8, "rgba(0,0,0,.13)"); g.addColorStop(1, "rgba(0,0,0,.6)");
    ctx.fillStyle = g; ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (!document.hidden) requestAnimationFrame(frame);
  }
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) { last = performance.now(); requestAnimationFrame(frame); }
  });
  window.addEventListener("pagehide", function () { try { sessionStorage.setItem("eoyBgTime", time); } catch (e) {} });
  requestAnimationFrame(frame);
})();
