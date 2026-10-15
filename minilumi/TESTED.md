# What we actually ran

Each preset was run end to end with `uv run minilumi run --input samples/hello.wav --badge EX-0001 --mute`:
a recorded question in, a spoken answer out. "Question to answer" is the time from the transcript
appearing to Lumi's first spoken sentence being ready.

| Preset | Machine | Hear | Think | Speak | Question to answer | Result | Date |
|---|---|---|---|---|---|---|---|
| workstation | NVIDIA DGX Spark (128 GB unified memory) | Parakeet server (OpenAI API) | Qwen3.8 Flash-Next via llama.cpp | Kokoro server (OpenAI API) | ≈ 1.3 s | ✓ correct room and directions | 2026-10-15 |
| laptop | same machine, CPU-only speech (stand-in for a laptop) | faster-whisper `base.en` (CPU) | Qwen3 1.7B Q8 via llama.cpp | kokoro-onnx (CPU) | ≈ 1.5 s | ✓ correct room | 2026-10-15 |
| cloud | — | — | — | — | — | not tested | — |

The laptop preset points at Ollama by default; we ran the same model through llama.cpp's
`llama-server` (OpenAI-compatible), not through Ollama itself.

macOS and Windows: the automated tests run on both in CI on every push; a full voice run there has
not been tested by us yet. If you try it, please open an issue and tell us how it went.
