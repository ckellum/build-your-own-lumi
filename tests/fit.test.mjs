import test from "node:test";
import assert from "node:assert";
import { HARDWARE, MODELS, assess, needGB, usableGB, biggestFit, pace } from "../js/fit-model.js";

const hw = (id) => HARDWARE.find((h) => h.id === id);
const model = (id) => MODELS.find((m) => m.id === id);
const near = (got, want, tolerance) => assert.ok(Math.abs(got - want) / want <= tolerance, `${got} vs ${want}`);

test("every model and machine has what the page needs", () => {
  for (const m of MODELS) assert.ok(m.gb > 0 && m.active > 0 && m.active <= m.gb && m.tasks.length && m.license, m.id);
  for (const h of HARDWARE) assert.ok(h.mem > 0 && h.bw > 0 && ["gpu", "unified", "cpu"].includes(h.kind), h.id);
  assert.equal(new Set(MODELS.map((m) => m.id)).size, MODELS.length);
});

test("memory: weights plus the conversation plus the runtime", () => {
  assert.equal(needGB(model("qwen35-9b")), 6.8);                        // 5.4 + 0.4 + 1.0
  assert.equal(needGB(model("qwen35-9b"), { context: "32k" }), 8.0);    // the conversation's memory ×4
  assert.equal(needGB(model("qwen35-9b"), { speech: true }), 9.8);      // + speech models on the same GPU
});

test("Macs give the GPU about two thirds of small memories and three quarters of large ones", () => {
  assert.equal(usableGB(hw("mac16")), 10.7);
  assert.equal(usableGB(hw("macmax64")), 48);
  assert.equal(usableGB(hw("spark")), 119);
});

test("the usual advice holds: 8 GB runs about 8B, 16 GB about 14B or a 20B mixture of experts", () => {
  assert.equal(assess(model("qwen35-9b"), hw("rtx4060")).verdict, "fits");
  assert.equal(assess(model("ministral3-14b"), hw("rtx4060")).verdict, "offload");
  assert.equal(assess(model("gptoss-20b"), hw("rtx5060ti")).verdict, "fits");
  assert.equal(assess(model("ministral3-14b"), hw("mac16")).verdict, "tight");
  assert.equal(assess(model("qwen38-27b"), hw("rtx5060ti")).verdict, "offload");
  assert.equal(assess(model("gptoss-120b"), hw("spark")).verdict, "fits");
  assert.equal(assess(model("gptoss-120b"), hw("mac32")).verdict, "no");      // a Mac can't offload past its memory
});

test("speed estimates land near published llama.cpp numbers", () => {
  near(assess(model("gptoss-120b"), hw("spark")).tps, 53, 0.3);     // jetsonhacks, b6767: 52.9 tok/s
  near(assess(model("gptoss-20b"), hw("spark")).tps, 80, 0.3);      // jetsonhacks: 79.7 tok/s
  near(assess(model("gptoss-120b"), hw("strix")).tps, 34, 0.35);    // ggml-org via Hardware Corner: 34.1
  const dense8b = { id: "x", name: "8B", gb: 4.8, active: 4.8, kv: 1, tasks: ["chat"], license: "x" };
  near(assess(dense8b, hw("rtx5090")).tps, 150, 0.35);              // Llama 3.1 8B Q4_K_M via Ollama: ~150
  near(assess(dense8b, hw("spark")).tps, 38, 0.3);                  // same model on the Spark: ~38
});

test("offloading to system RAM is slower than fitting", () => {
  const fits = assess(model("qwen36-35b"), hw("rtx3090"));
  const offloaded = assess(model("qwen36-35b"), hw("rtx5080"));
  assert.ok(["fits", "tight"].includes(fits.verdict));
  assert.equal(offloaded.verdict, "offload");
  assert.ok(offloaded.tps < assess(model("qwen36-35b"), hw("rtx5090")).tps);
});

test("the biggest model that fits grows with memory", () => {
  assert.equal(biggestFit(hw("rtx4060")).id, "qwen35-9b");
  assert.equal(biggestFit(hw("spark")).id, "qwen35-122b");
  assert.ok(MODELS.indexOf(biggestFit(hw("rtx5060ti"))) > MODELS.indexOf(biggestFit(hw("rtx4060"))));
});

test("pace words for the speeds", () => {
  assert.match(pace(80), /faster than you can read/);
  assert.match(pace(3), /slow/);
  assert.equal(pace(null), "");
});

test("speeds stay sensible even when the conversation spills into system RAM", () => {
  const a = assess(model("qwen35-4b"), hw("rtx4060"), { context: "128k", speech: true });
  assert.ok(a.tps > 0 && Number.isFinite(a.tps));
});
