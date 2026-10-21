// "Will it run?": which local models fit a GPU or Mac, and roughly how fast they talk.
// Pure data and math (no DOM), so tests/fit.test.mjs can check it in Node.
//
// Memory: weights at 4-bit (Q4_K_M, about 0.6 GB per billion parameters) + the conversation's
// memory (KV cache, grows with context) + about 1 GB for the runtime.
// Speed: writing each token reads the model's active weights from memory once, so
//   seconds per token ≈ active GB / (bandwidth × efficiency) + a fixed per-token overhead.
// Checked against published llama.cpp numbers (tests/fit.test.mjs): rough, ±30–40%.

export const RUNTIME_GB = 1.0;
export const SPEECH_GB = 3.0;           // speech-to-text + a voice, if they share the GPU
const RAM_BW = 60;                      // GB/s: typical dual-channel desktop RAM, for offloaded layers
const RAM_SHARE = 0.6;                  // how much system RAM is fair to give a model

// kind: gpu (dedicated VRAM, can offload to system RAM), unified (Mac, Spark, Strix Halo), cpu.
// Mac speeds are the M5 generation (Apple's spec pages). usable: what a model may use. Macs let the GPU use about 2/3 of RAM up to 36 GB, about 3/4 above.
export const HARDWARE = [
  { id: "rtx4060", group: "NVIDIA GPU", name: "RTX 4060 · 8 GB", kind: "gpu", mem: 8, bw: 272 },
  { id: "rtx3060", group: "NVIDIA GPU", name: "RTX 3060 · 12 GB", kind: "gpu", mem: 12, bw: 360 },
  { id: "rtx4070", group: "NVIDIA GPU", name: "RTX 4070 / 4070 Super · 12 GB", kind: "gpu", mem: 12, bw: 504 },
  { id: "rtx5070", group: "NVIDIA GPU", name: "RTX 5070 · 12 GB", kind: "gpu", mem: 12, bw: 672 },
  { id: "rtx4060ti", group: "NVIDIA GPU", name: "RTX 4060 Ti · 16 GB", kind: "gpu", mem: 16, bw: 288 },
  { id: "rtx5060ti", group: "NVIDIA GPU", name: "RTX 5060 Ti · 16 GB", kind: "gpu", mem: 16, bw: 448 },
  { id: "rtx5080", group: "NVIDIA GPU", name: "RTX 5080 · 16 GB", kind: "gpu", mem: 16, bw: 960 },
  { id: "rtx3090", group: "NVIDIA GPU", name: "RTX 3090 · 24 GB", kind: "gpu", mem: 24, bw: 936 },
  { id: "rtx4090", group: "NVIDIA GPU", name: "RTX 4090 · 24 GB", kind: "gpu", mem: 24, bw: 1008 },
  { id: "rtx5090", group: "NVIDIA GPU", name: "RTX 5090 · 32 GB", kind: "gpu", mem: 32, bw: 1792 },
  { id: "mac16", group: "Apple Silicon Mac", name: "Mac, M-series · 16 GB", kind: "unified", mem: 16, bw: 150 },
  { id: "mac24", group: "Apple Silicon Mac", name: "Mac, M-series · 24 GB", kind: "unified", mem: 24, bw: 150 },
  { id: "mac32", group: "Apple Silicon Mac", name: "Mac, M-series · 32 GB", kind: "unified", mem: 32, bw: 150 },
  { id: "macpro24", group: "Apple Silicon Mac", name: "Mac, Pro chip · 24 GB", kind: "unified", mem: 24, bw: 307 },
  { id: "macpro48", group: "Apple Silicon Mac", name: "Mac, Pro chip · 48 GB", kind: "unified", mem: 48, bw: 307 },
  { id: "macpro64", group: "Apple Silicon Mac", name: "Mac, Pro chip · 64 GB", kind: "unified", mem: 64, bw: 307 },
  { id: "macmax36", group: "Apple Silicon Mac", name: "Mac, Max chip · 36 GB", kind: "unified", mem: 36, bw: 460 },
  { id: "macmax64", group: "Apple Silicon Mac", name: "Mac, Max chip · 64 GB", kind: "unified", mem: 64, bw: 614 },
  { id: "macmax128", group: "Apple Silicon Mac", name: "Mac, Max chip · 128 GB", kind: "unified", mem: 128, bw: 614 },
  { id: "spark", group: "AI desktops", name: "NVIDIA DGX Spark · 128 GB (Lumi's)", kind: "unified", mem: 128, bw: 273, usable: 119, nvidia: true },
  { id: "strix", group: "AI desktops", name: "AMD Ryzen AI Max+ 395 · 128 GB", kind: "unified", mem: 128, bw: 256, usable: 96 },
  { id: "cpu16", group: "No GPU", name: "Laptop or PC, no GPU · 16 GB RAM", kind: "cpu", mem: 16, bw: 60, usable: 10 },
  { id: "cpu32", group: "No GPU", name: "Laptop or PC, no GPU · 32 GB RAM", kind: "cpu", mem: 32, bw: 60, usable: 24 },
];

// gb: weights at the listed quant. active: GB read per token (all of it for dense models, only the
// chosen experts for mixture-of-experts). kv: the conversation's memory at 8K tokens (rough).
// tasks: chat, tools (tool calling, home automation), code, vision.
export const MODELS = [
  { id: "qwen35-4b", name: "Qwen3.5 4B", gb: 2.4, active: 2.4, kv: 0.3, tasks: ["chat", "tools", "vision"], license: "Apache 2.0", note: "Small and quick. Did very well in tool-calling tests for its size." },
  { id: "gemma4-e4b", name: "Gemma 4 E4B", gb: 3.8, active: 3.8, kv: 0.3, tasks: ["chat", "vision"], license: "Apache 2.0", note: "Google's small model. Understands images, and audio too." },
  { id: "ministral3-8b", name: "Ministral 3 8B", gb: 4.9, active: 4.9, kv: 1.0, tasks: ["chat", "tools", "code", "vision"], license: "Apache 2.0", note: "Mistral's 8B, with image input." },
  { id: "granite41-8b", name: "Granite 4.1 8B", gb: 4.9, active: 4.9, kv: 1.0, tasks: ["chat", "tools"], license: "Apache 2.0", note: "IBM's business-focused model." },
  { id: "qwen35-9b", name: "Qwen3.5 9B", gb: 5.4, active: 5.4, kv: 0.4, tasks: ["chat", "tools", "code", "vision"], license: "Apache 2.0", note: "A strong all-rounder for 8 GB cards." },
  { id: "gemma4-12b", name: "Gemma 4 12B", gb: 7.0, active: 7.0, kv: 0.8, tasks: ["chat", "vision"], license: "Apache 2.0", note: "A good step up on 12 GB cards and 16 GB Macs." },
  { id: "ministral3-14b", name: "Ministral 3 14B", gb: 8.4, active: 8.4, kv: 1.2, tasks: ["chat", "tools", "code", "vision"], license: "Apache 2.0", note: "The most capable dense model for 12 GB." },
  { id: "gptoss-20b", name: "gpt-oss-20b", gb: 12.0, active: 2.0, kv: 0.4, tasks: ["chat", "tools", "code"], license: "Apache 2.0", moe: true, note: "OpenAI's open model. Mixture of experts: fast for its size. Text only." },
  { id: "gemma4-26b", name: "Gemma 4 26B-A4B", gb: 14.0, active: 2.4, kv: 0.6, tasks: ["chat", "tools", "vision"], license: "Apache 2.0", moe: true, note: "Mixture of experts: about 4B active per token, so it's quick." },
  { id: "devstral2-24b", name: "Devstral Small 2 24B", gb: 14.4, active: 14.4, kv: 1.3, tasks: ["code"], license: "check the model card", note: "Mistral's coding model. Tight on 16 GB." },
  { id: "qwen38-27b", name: "Qwen3.8 27B", gb: 16.2, active: 16.2, kv: 0.5, tasks: ["chat", "tools", "code", "vision"], license: "Apache 2.0", note: "The newest Qwen dense model. Images and video in." },
  { id: "gemma4-31b", name: "Gemma 4 31B", gb: 18.6, active: 18.6, kv: 1.5, tasks: ["chat", "vision"], license: "Apache 2.0", note: "Google's largest Gemma 4." },
  { id: "qwen36-35b", name: "Qwen3.6 35B-A3B", gb: 21.0, active: 1.8, kv: 0.4, tasks: ["chat", "tools", "code", "vision"], license: "Apache 2.0", moe: true, note: "Only about 3B active per token: fast, even partly in system RAM." },
  { id: "gptoss-120b", name: "gpt-oss-120b", gb: 63.0, active: 3.0, kv: 0.6, tasks: ["chat", "tools", "code"], license: "Apache 2.0", moe: true, note: "A big mixture of experts. The kind of model 128 GB machines are for." },
  { id: "qwen35-122b", name: "Qwen3.5 122B-A10B", gb: 73.0, active: 6.0, kv: 0.6, tasks: ["chat", "tools", "code", "vision"], license: "Apache 2.0", moe: true, note: "Near-frontier for home hardware, if you have the memory." },
];

export const CONTEXTS = { "8k": 1, "32k": 4, "128k": 16 };

export function usableGB(hw) {
  if (hw.usable) return hw.usable;
  if (hw.kind === "gpu") return hw.mem - 0.5;                 // the desktop keeps a little
  if (hw.kind === "unified") return Math.round(hw.mem * (hw.mem <= 36 ? 0.67 : 0.75) * 10) / 10;
  return hw.mem * 0.6;
}

export function needGB(model, { context = "8k", speech = false } = {}) {
  const kv = model.kv * (CONTEXTS[context] || 1);
  return round1(model.gb + kv + RUNTIME_GB + (speech ? SPEECH_GB : 0));
}

function perToken(hw) {
  // efficiency of the memory reads, and a fixed cost per token (kernel launches, sampling)
  if (hw.kind === "gpu" || hw.nvidia) return { eff: 0.75, fixed: 0.0025 };
  return { eff: 0.6, fixed: 0.005 };
}

// verdict: fits (comfortable), tight (fits, little room to spare), offload (part in system RAM), no.
export function assess(model, hw, { context = "8k", speech = false, ram = 32 } = {}) {
  const need = needGB(model, { context, speech });
  const have = usableGB(hw);
  const { eff, fixed } = perToken(hw);
  let verdict, inRam = 0;
  if (need <= have - Math.max(0.5, have * 0.05)) verdict = "fits";      // room to spare
  else if (need <= have) verdict = "tight";
  else if (hw.kind === "gpu" && need <= have + ram * RAM_SHARE) { verdict = "offload"; inRam = need - have; }
  else verdict = "no";
  let tps = null;
  if (verdict !== "no") {
    const ramShare = Math.min(1, inRam / model.gb);                         // the part of the weights left in RAM
    const fast = model.active * (1 - ramShare), slow = model.active * ramShare;
    const seconds = fast / (hw.bw * eff) + slow / (RAM_BW * 0.7) + fixed;
    tps = Math.round(1 / seconds);
  }
  return { need, have, verdict, tps };
}

export function biggestFit(hw, opts = {}) {
  const fits = MODELS.filter((m) => ["fits", "tight"].includes(assess(m, hw, opts).verdict));
  return fits.length ? fits[fits.length - 1] : null;
}

export function pace(tps) {
  if (tps == null) return "";
  if (tps >= 40) return "faster than you can read";
  if (tps >= 7) return "about reading speed or faster";
  if (tps >= 4) return "slower than reading: fine for short answers";
  return "slow: a word at a time";
}

function round1(x) { return Math.round(x * 10) / 10; }
