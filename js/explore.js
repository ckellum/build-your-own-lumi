// Explore pages: the depth switch (shared with the guide), copy buttons, gentle reveals.
import { LEVELS, readChoice, saveChoice, applyChoice } from "./picker.js";

const root = document.documentElement;
let storage;
try { storage = window.localStorage; } catch { storage = undefined; }

const buttons = [...document.querySelectorAll("[data-set-level]")];
const setLevel = (value, remember) => {
  applyChoice(root, "level", value);
  buttons.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.setLevel === value)));
  if (remember) saveChoice(storage, "lumi-level", value);
};
buttons.forEach((b) => b.addEventListener("click", () => setLevel(b.dataset.setLevel, true)));
setLevel(readChoice(storage, "lumi-level", LEVELS, "beginner"), false);

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
    try {
      await navigator.clipboard.writeText(pre.innerText.replace(/^\s*#.*$/gm, "").replace(/\n{2,}/g, "\n").trim());
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
if (window.gsap && window.ScrollTrigger && !reduced) {
  gsap.registerPlugin(ScrollTrigger);
  root.classList.add("reveal-ready");
  ScrollTrigger.batch("[data-reveal]", {
    start: "top 90%",
    onEnter: (els) => gsap.to(els, { opacity: 1, y: 0, duration: 0.6, stagger: 0.06, ease: "power3.out", overwrite: true }),
  });
  gsap.to(".progress", { scaleX: 1, ease: "none", scrollTrigger: { start: 0, end: "max", scrub: 0.2 } });
}
