# LiveCopilot 2.0.0

## Features

- Jev Mode: local Laya evaluates complete Apple/Paraformer speech segments and, after a pause, uses an adjustable threshold to trigger analysis. GPT-Live-1 keeps its own semantic delegation and does not use Jev Mode trigger settings.
- GPT-Live-1 language preferences: Chinese-first, English-first, mixed Chinese/English, or unrestricted automatic recognition. These are session prompts, not guaranteed language restrictions.
- BGE, Paraformer, Silero VAD, Laya, and isolated Python dependencies download from an immutable public ModelScope revision, verify each SHA-256, and fall back to configured mirrors/upstream. No AccessKey is embedded. UI shows file number, actual progress, and speed.
- Fixed local speech startup, streaming captions, automatic scheduling, and soft-frost header; updated OpenAI branding in Settings.

## Installation and compatibility

macOS 14+, universal Apple Silicon/Intel. Laya requires Apple Silicon; Apple Speech additionally requires macOS 26+ and supported hardware. Quit before replacing `LiveCopilot.app`. Models, sessions, settings, knowledge, and Keychain credentials remain; private data is not included in the package.

Automatic triggering can miss or misclassify intent; manual generation remains available. Laya classifies only; the chosen analysis service produces answers and may charge API fees. GPT-Live-1 sends audio to OpenAI, with speech and analysis billed separately.

See [ModelScope distribution](MODELSCOPE_MODEL_DISTRIBUTION.md) and [per-file manifest](oss-model-manifest.json) for delivery/licenses.
