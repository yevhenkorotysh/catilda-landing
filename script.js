/* ABOUTME: Ambient starfield canvas and small landing page bootstrapping. */
/* ABOUTME: Respects prefers-reduced-motion; draws sparse drifting stars. */

(function () {
  const year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());

  const canvas = document.getElementById("starfield");
  if (!canvas || !canvas.getContext) return;

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const ctx = canvas.getContext("2d");
  let stars = [];
  let width = 0;
  let height = 0;
  let raf = 0;

  function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    seed();
  }

  function seed() {
    const count = Math.floor((width * height) / 9000);
    stars = [];
    for (let i = 0; i < count; i += 1) {
      stars.push({
        x: Math.random() * width,
        y: Math.random() * height,
        r: Math.random() * 1.4 + 0.2,
        a: Math.random() * 0.7 + 0.15,
        s: Math.random() * 0.15 + 0.02,
        tw: Math.random() * Math.PI * 2,
      });
    }
  }

  function draw(t) {
    ctx.clearRect(0, 0, width, height);
    for (let i = 0; i < stars.length; i += 1) {
      const star = stars[i];
      const twinkle = 0.55 + 0.45 * Math.sin(t * 0.001 + star.tw);
      ctx.beginPath();
      ctx.fillStyle = "rgba(242, 238, 248," + star.a * twinkle + ")";
      ctx.arc(star.x, star.y, star.r, 0, Math.PI * 2);
      ctx.fill();
      if (!reduceMotion) {
        star.y += star.s;
        if (star.y > height + 2) {
          star.y = -2;
          star.x = Math.random() * width;
        }
      }
    }
    if (!reduceMotion) raf = requestAnimationFrame(draw);
  }

  resize();
  draw(0);
  window.addEventListener("resize", function () {
    cancelAnimationFrame(raf);
    resize();
    draw(0);
  });
})();
