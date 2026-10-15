// Wires up the page: picker and depth switch, copy buttons, reveals, progress bar.
import { TIERS, LEVELS, readChoice, saveChoice, applyChoice } from "./picker.js";
import { mountAvatar } from "./avatar.js";
import { mountPipeline } from "./pipeline.js";

const root = document.documentElement;
let storage;
try { storage = window.localStorage; } catch { storage = undefined; }

function bindChoice(attr, allowed, fallback) {
  const value = readChoice(storage, `lumi-${attr}`, allowed, fallback);
  const buttons = [...document.querySelectorAll(`[data-set-${attr}]`)];
  const set = (v, remember) => {
    applyChoice(root, attr, v);
    buttons.forEach((b) => b.setAttribute("aria-pressed", String(b.getAttribute(`data-set-${attr}`) === v)));
    if (remember) saveChoice(storage, `lumi-${attr}`, v);
    if (window.ScrollTrigger) ScrollTrigger.refresh();
  };
  buttons.forEach((b) => b.addEventListener("click", () => set(b.getAttribute(`data-set-${attr}`), true)));
  set(value, false);
}
bindChoice("tier", TIERS, "laptop");
bindChoice("level", LEVELS, "beginner");

// Copy buttons on every code block.
document.querySelectorAll("pre").forEach((pre) => {
  const wrap = document.createElement("div");
  wrap.className = "code";
  pre.replaceWith(wrap);
  wrap.append(pre);
  const button = document.createElement("button");
  button.className = "copy";
  button.type = "button";
  button.textContent = "copy";
  button.addEventListener("click", async () => {
    const text = [...pre.querySelectorAll("code")].map((c) => c.innerText).join("\n") || pre.innerText;
    try {
      await navigator.clipboard.writeText(text.replace(/^\s*#.*$/gm, "").replace(/\n{2,}/g, "\n").trim());
      button.textContent = "copied";
      button.classList.add("done");
    } catch {
      button.textContent = "select + copy";
    }
    setTimeout(() => { button.textContent = "copy"; button.classList.remove("done"); }, 1600);
  });
  wrap.append(button);
});

const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
if (window.gsap && window.ScrollTrigger) gsap.registerPlugin(ScrollTrigger);
mountAvatar(document.querySelector(".avatar-stage"), document.querySelector(".avatar-caption"));
mountPipeline(document.querySelector(".pipeline"));

if (window.gsap && window.ScrollTrigger && !reduced) {
  root.classList.add("reveal-ready");
  ScrollTrigger.batch("[data-reveal]", {
    start: "top 88%",
    onEnter: (els) => gsap.to(els, { opacity: 1, y: 0, duration: 0.7, stagger: 0.08, ease: "power3.out", overwrite: true }),
  });
  gsap.to(".progress", { scaleX: 1, ease: "none", scrollTrigger: { start: 0, end: "max", scrub: 0.2 } });
  gsap.from(".hero [data-hero]", { opacity: 0, y: 30, duration: 0.9, stagger: 0.12, ease: "power3.out" });
}
