// The "Will it run?" page: pick a machine, see which models fit and roughly how fast they talk.
import { HARDWARE, MODELS, assess, usableGB, biggestFit, pace } from "./fit-model.js";

const $ = (id) => document.getElementById(id);
const els = { hw: $("fit-hw"), ram: $("fit-ram"), ctx: $("fit-ctx"), task: $("fit-task"), speech: $("fit-speech"),
  ramWrap: $("fit-ram-wrap"), list: $("fit-list"), summary: $("fit-summary") };
if (els.hw) {
  let storage;
  try { storage = window.localStorage; } catch { storage = undefined; }
  const remembered = (() => { try { return storage?.getItem("lumi-fit-hw"); } catch { return null; } })();

  const groups = {};
  for (const h of HARDWARE) (groups[h.group] ||= []).push(h);
  for (const [name, items] of Object.entries(groups)) {
    const group = document.createElement("optgroup");
    group.label = name;
    for (const h of items) group.append(new Option(h.name, h.id));
    els.hw.append(group);
  }
  els.hw.value = HARDWARE.some((h) => h.id === remembered) ? remembered : "rtx5060ti";

  const label = { fits: "Fits", tight: "Fits, just", offload: "Runs, partly in system RAM", no: "Doesn't fit" };
  const order = { fits: 0, tight: 1, offload: 2, no: 3 };

  const render = () => {
    const hw = HARDWARE.find((h) => h.id === els.hw.value);
    try { storage?.setItem("lumi-fit-hw", hw.id); } catch { /* not remembered */ }
    els.ramWrap.hidden = hw.kind !== "gpu";
    const opts = { context: els.ctx.value, speech: els.speech.checked, ram: Number(els.ram.value) };
    const have = usableGB(hw);
    const big = biggestFit(hw, opts);
    els.summary.replaceChildren(
      stat(`${have} GB`, hw.kind === "gpu" ? "for models (VRAM)" : hw.kind === "cpu" ? "of RAM for models" : "of unified memory for models"),
      stat(`${hw.bw} GB/s`, "memory speed"),
      stat(big ? big.name : "a 4B model, tight", "biggest that fits fully"),
    );
    const rows = MODELS.filter((m) => els.task.value === "all" || m.tasks.includes(els.task.value))
      .map((m) => ({ m, a: assess(m, hw, opts) }))
      .sort((x, y) => order[x.a.verdict] - order[y.a.verdict] || (x.a.verdict === "no" ? x.m.gb - y.m.gb : y.m.gb - x.m.gb));
    els.list.replaceChildren(...rows.map(({ m, a }) => item(m, a)));
  };

  function stat(value, text) {
    const d = document.createElement("div");
    d.className = "stat";
    d.innerHTML = "<b></b><span></span>";
    d.querySelector("b").textContent = value;
    d.querySelector("span").textContent = text;
    return d;
  }

  function item(m, a) {
    const d = document.createElement("article");
    d.className = "fit-item" + (a.verdict === "no" ? " is-no" : "");
    const pct = Math.min(100, Math.round((a.need / a.have) * 100));
    d.innerHTML = `<div class="head"><span class="name"></span><span class="verdict v-${a.verdict}"></span></div>
      <div class="bar${a.need > a.have ? " over" : ""}" role="img"><i style="width:${pct}%"></i></div>
      <div class="nums"><span>needs <b></b></span><span class="speed"></span><span class="lic"></span><span class="tasks"></span></div><p></p>`;
    d.querySelector(".name").textContent = m.name + (m.moe ? " · mixture of experts" : "");
    d.querySelector(".verdict").textContent = label[a.verdict];
    d.querySelector(".bar").setAttribute("aria-label", `needs ${a.need} of ${a.have} GB`);
    d.querySelector(".nums b").textContent = `${a.need} GB of ${a.have}`;
    d.querySelector(".speed").textContent = a.tps ? `~${a.tps} tokens/s · ${pace(a.tps)}` : "";
    d.querySelector(".lic").textContent = m.license;
    d.querySelector(".tasks").textContent = m.tasks.map((t) => ({ chat: "chat", tools: "tools", code: "code", vision: "images" }[t])).join(" · ");
    d.querySelector("p").textContent = m.note;
    return d;
  }

  for (const el of [els.hw, els.ram, els.ctx, els.task, els.speech]) el.addEventListener("change", render);
  render();
}
