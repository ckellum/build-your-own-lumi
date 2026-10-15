// "What you're building": a pinned, scroll-driven pipeline. A pulse travels the path
// and each stage lights up as it arrives; the side panel explains the current stage.

const STAGES = [
  { tag: "1 · Wake", title: "A badge scan starts a visit",
    text: "Press Enter or scan a badge. A USB barcode or QR scanner types like a keyboard, so it works with no extra code. The mic only opens during a visit.",
    file: "cli.py" },
  { tag: "2 · Hear", title: "Speech becomes text",
    text: "Lumi waits until you stop talking, then a speech-to-text model (Whisper or Parakeet) writes down what you said.",
    file: "listen.py · hear.py" },
  { tag: "3 · Think", title: "A language model answers",
    text: "The event's rooms, sessions and facts sit in the system prompt. Your name, the time and your sessions ride along with your first question.",
    file: "event.py · think.py" },
  { tag: "4 · Speak", title: "Text becomes a voice",
    text: "Each sentence is spoken as soon as it's written, so Lumi starts talking before the model has finished thinking.",
    file: "speak.py" },
  { tag: "5 · Show", title: "A face that talks",
    text: "A browser page shows the avatar, captions and what Lumi heard. The mouth follows the loudness of the audio.",
    file: "screen.py · ui/" },
];

export function mountPipeline(section) {
  const svg = section.querySelector(".pipe-svg");
  const path = svg.querySelector(".track");
  const glowPath = svg.querySelector(".glow");
  const pulse = svg.querySelector(".pulse");
  const nodes = [...svg.querySelectorAll(".pipe-node")];
  const panel = section.querySelector(".pipe-panel");
  const length = path.getTotalLength();
  // Where along the path each node sits (0..1): the sampled point nearest its centre.
  const samples = Array.from({ length: 401 }, (_, i) => path.getPointAtLength((i / 400) * length));
  const stops = nodes.map((n) => {
    const cx = Number(n.dataset.x), cy = Number(n.dataset.y);
    let best = 0, bestD = Infinity;
    samples.forEach((p, i) => { const d = (p.x - cx) ** 2 + (p.y - cy) ** 2; if (d < bestD) { bestD = d; best = i; } });
    return best / 400;
  });
  let current = -1;

  function show(i) {
    if (i === current) return;
    current = i;
    const s = STAGES[Math.max(0, i)];
    panel.querySelector(".step-tag").textContent = s.tag;
    panel.querySelector("h3").textContent = s.title;
    panel.querySelector("p").textContent = s.text;
    panel.querySelector("code").textContent = s.file;
    if (window.gsap) gsap.fromTo(panel, { opacity: 0.35, y: 8 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" });
  }

  function render(progress) {
    const at = progress * length;
    const p = path.getPointAtLength(at);
    pulse.setAttribute("cx", p.x);
    pulse.setAttribute("cy", p.y);
    glowPath.style.strokeDasharray = `${length}`;
    glowPath.style.strokeDashoffset = `${length - at}`;
    let lit = -1;
    nodes.forEach((n, i) => {
      const on = progress >= stops[i] - 0.001;
      n.classList.toggle("on", on);
      if (on) lit = i;
    });
    show(Math.max(0, lit));
  }

  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced || !window.gsap || !window.ScrollTrigger) {
    render(1);
    return;
  }
  // Pin only on wide screens: on a phone the stage + text is taller than the screen, so pinning
  // would hold the explanation below the fold. Phones scrub as the section scrolls past instead.
  ScrollTrigger.matchMedia({
    "(min-width: 900px)": () => {
      render(0);
      ScrollTrigger.create({ trigger: section, start: "top top", end: "+=1600", pin: true, scrub: 0.6,
        onUpdate: (self) => render(self.progress) });
    },
    "(max-width: 899px)": () => {
      render(0);
      ScrollTrigger.create({ trigger: section.querySelector(".pipe-svg"), start: "top 75%", end: "bottom 35%", scrub: 0.6,
        onUpdate: (self) => render(self.progress) });
    },
  });
}
