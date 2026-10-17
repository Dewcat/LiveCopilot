# Local model downloads (2026-09-23 development record)

This is a historical record. See [ModelScope distribution](MODELSCOPE_MODEL_DISTRIBUTION.md) and [current release readiness](MODEL_RELEASE_READINESS.md) for later changes.

The application chooses download sources automatically: mirrors first, then upstream. Old source preferences no longer apply. Third-party mirrors do not guarantee mainland availability or a mainland redirect destination.

| Content | Preferred mirror | Upstream |
| --- | --- | --- |
| BGE-M3 Q8; Paraformer encoder, decoder, vocabulary | HF-Mirror | Hugging Face |
| Laya model, tokenizer, configuration | HF-Mirror | Hugging Face |
| Pinned Laya Python wheels | Tsinghua PyPI mirror | files.pythonhosted.org |
| Silero VAD | No verified alternative at this checkpoint | GitHub Releases |
| Isolated Laya Python and source | No verified alternative at this checkpoint | GitHub Releases / codeload |
| Apple ASR | System managed | Apple |

Every source uses the same pinned SHA-256. A checksum failure prevents installation and causes another source to be tried. Existing models do not require another download or index rebuild.

BGE/Paraformer show the current file's percentage, downloaded MB, MB/s, and source hostname. Unknown Content-Length shows only bytes and speed. Progress resets for each file/source. Network retries retain URLSession resume data when available; resuming across cancellation or exit is not promised. Laya retains a persistent chunk cache and reports completed model bytes, not whole-installation speed.

The official BAAI platform was reachable, but a verified official URL for the GPUStack Q8 GGUF was not established, so no speculative URL was added. At this checkpoint the user had no domestic object storage; no models were uploaded and no hosting service was created.

Validation downloaded Laya LICENSE, encoder/config.json, and a pinned PyPI wheel through mirrors and matched existing hashes. curl used `--noproxy '*'`; this does not exclude system VPNs or transparent routing. A full fresh installation on a verified proxy-free network was not tested. Some mirror responses still redirected to Hugging Face/CDN.

## 20260923.002

Removed manual source selection and ignored old preferences. Laya's Python archive reports URLSession bytes/speed; other downloads report written bytes and interval speed every 0.5 seconds, excluding cached bytes. Unknown totals use an indeterminate indicator and byte counts rather than invented percentages. Installation/verification uses stage progress. Apple's speech-resource API exposes no download bytes or speed. Existing downloads were retained.

## 20260923.003

Added local-model deletion for BGE/Paraformer and deletion of Laya models, runtime, and download cache. Actions require confirmation and are disabled while busy. BGE stops its resident inference process first; knowledge documents, indexes, and settings remain. Shared Apple language assets are not directly deleted. Deletion tests used only temporary synthetic data; installing the update does not clear real models.
