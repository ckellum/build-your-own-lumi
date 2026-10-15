// Lumi talk deck. Plain script (no modules) so it runs from file:// with no server.
// Keys: → Space PageDown next · ← PageUp back · Home/End · P presenter view · F full screen.
(function () {
  const REPO = "github.com/ckellum/build-your-own-lumi";
  const slides = [...document.querySelectorAll(".slide")];
  const stage = document.getElementById("stage");
  const presenterMode = new URLSearchParams(location.search).has("presenter");
  let index = 0, presenter = null, startedAt = null;

  // Footer + section tag on every slide.
  slides.forEach((slide, i) => {
    const foot = document.createElement("div");
    foot.className = "foot";
    foot.innerHTML = `<b>${REPO}</b><span>${i + 1} / ${slides.length}</span>`;
    slide.append(foot);
    if (slide.dataset.section) {
      const tag = document.createElement("div");
      tag.className = "section-tag";
      tag.textContent = slide.dataset.section;
      slide.prepend(tag);
    }
  });

  function fit() {
    const scale = Math.min(innerWidth / 1920, innerHeight / 1080);
    stage.style.transform = `scale(${scale})`;
  }
  addEventListener("resize", fit);
  fit();

  // Videos: play on entry, pause on exit; a missing file shows a labelled placeholder.
  document.querySelectorAll(".video-full video").forEach((video) => {
    const mark = () => video.closest(".video-full").classList.add("missing");
    video.addEventListener("error", mark, true);
    video.querySelectorAll("source").forEach((s) => s.addEventListener("error", mark));
    video.addEventListener("click", () => (video.paused ? video.play() : video.pause()));
  });

  function animatePipeline(slide) {
    const svg = slide.querySelector(".pipe");
    const path = svg.querySelector(".track"), glow = svg.querySelector(".glow"), pulse = svg.querySelector(".pulse");
    const nodes = [...svg.querySelectorAll(".node")];
    const length = path.getTotalLength();
    const stops = nodes.map((n) => {
      const x = Number(n.dataset.x);
      let best = 0, bestD = Infinity;
      for (let i = 0; i <= 300; i++) {
        const p = path.getPointAtLength((i / 300) * length), d = Math.abs(p.x - x);
        if (d < bestD) { bestD = d; best = i / 300; }
      }
      return best;
    });
    const state = { p: 0 };
    const draw = () => {
      const p = path.getPointAtLength(state.p * length);
      pulse.setAttribute("cx", p.x); pulse.setAttribute("cy", p.y);
      glow.style.strokeDasharray = length; glow.style.strokeDashoffset = length - state.p * length;
      nodes.forEach((n, i) => n.classList.toggle("on", state.p >= stops[i] - 0.002));
    };
    if (!window.gsap) { state.p = 1; draw(); return; }
    gsap.killTweensOf(state);
    state.p = 0; draw();
    gsap.to(state, { p: 1, duration: 6, ease: "power1.inOut", onUpdate: draw, delay: 0.4 });
  }

  function enter(slide) {
    const items = slide.querySelectorAll("[data-a]");
    if (window.gsap && items.length) {
      gsap.fromTo(items, { opacity: 0, y: 34 }, { opacity: 1, y: 0, duration: 0.7, stagger: 0.1, ease: "power3.out", overwrite: true });
    }
    if (slide.dataset.anim === "pipeline") animatePipeline(slide);
    const video = slide.querySelector("video");
    if (video) { video.currentTime = 0; video.play().catch(() => {}); }
  }

  function go(n, push = true) {
    n = Math.max(0, Math.min(slides.length - 1, n));
    slides[index].querySelectorAll("video").forEach((v) => v.pause());
    slides[index].classList.remove("active");
    index = n;
    const slide = slides[index];
    slide.classList.add("active");
    if (window.gsap) gsap.fromTo(slide, { opacity: 0 }, { opacity: 1, duration: 0.45, ease: "power2.out" });
    enter(slide);
    if (push) history.replaceState(null, "", `#${index + 1}`);
    if (!startedAt && index > 0) startedAt = Date.now();
    sync();
  }

  function info(i) {
    const s = slides[i];
    if (!s) return { title: "— end —", notes: "" };
    const h = s.querySelector("h1, h2, h3");
    return { title: s.dataset.title || (h ? h.textContent.trim() : `Slide ${i + 1}`), notes: (s.dataset.notes || "").trim() };
  }

  function sync() {
    const payload = { type: "lumi-deck", index, total: slides.length, now: info(index), next: info(index + 1), startedAt };
    if (presenter && !presenter.closed) presenter.postMessage(payload, "*");
  }

  // Presenter window: same file with ?presenter. Talks to the main window with postMessage
  // (works from file://, where BroadcastChannel and cross-window DOM access do not).
  function openPresenter() {
    presenter = window.open(location.pathname + "?presenter", "lumi-presenter", "width=1100,height=760");
    setTimeout(sync, 600);
  }

  if (presenterMode) {
    document.body.classList.add("presenter");
    const view = document.getElementById("presenter");
    let state = null;
    const render = () => {
      if (!state) return;
      const mins = state.startedAt ? Math.floor((Date.now() - state.startedAt) / 60000) : 0;
      const secs = state.startedAt ? Math.floor((Date.now() - state.startedAt) / 1000) % 60 : 0;
      view.innerHTML = `
        <div class="meta"><span>${state.index + 1} / ${state.total}</span><span>${mins}:${String(secs).padStart(2, "0")} elapsed</span><span>←/→ to drive the deck</span></div>
        <div class="now"><span class="dim">NOW</span><h2>${state.now.title}</h2></div>
        <div class="next"><span class="dim">NEXT</span><h2>${state.next.title}</h2></div>
        <div class="notes">${state.now.notes.replace(/</g, "&lt;")}</div>`;
    };
    addEventListener("message", (e) => { if (e.data && e.data.type === "lumi-deck") { state = e.data; render(); } });
    setInterval(render, 1000);
    addEventListener("keydown", (e) => { if (window.opener) window.opener.postMessage({ type: "lumi-key", key: e.key }, "*"); });
    return;
  }

  addEventListener("message", (e) => { if (e.data && e.data.type === "lumi-key") key(e.data.key); });

  function key(k) {
    if (["ArrowRight", " ", "PageDown", "ArrowDown", "Enter"].includes(k)) go(index + 1);
    else if (["ArrowLeft", "PageUp", "ArrowUp", "Backspace"].includes(k)) go(index - 1);
    else if (k === "Home") go(0);
    else if (k === "End") go(slides.length - 1);
    else if (k === "p" || k === "P") openPresenter();
    else if (k === "f" || k === "F") document.documentElement.requestFullscreen?.();
  }
  addEventListener("keydown", (e) => {
    if (e.target.closest && e.target.closest("video")) return;
    if ([" ", "PageDown", "PageUp", "ArrowDown", "ArrowUp"].includes(e.key)) e.preventDefault();
    key(e.key);
  });

  const fromHash = parseInt(location.hash.slice(1), 10);
  slides[0].classList.add("active");
  go(Number.isFinite(fromHash) ? fromHash - 1 : 0, false);
})();
