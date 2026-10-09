# Licensing, privacy and development

[← Project overview](../README.md) · [Documentation index](README.md)

## Attribution and license boundary

Local FastAPI integration by **Jesús Pacheco / Akitá** for the independent
[OmniVoice upstream project](https://github.com/k2-fsa/OmniVoice). The upstream
model and research are by Han Zhu and collaborators, not by the integration
maintainer. This repository supplies REST/WebSocket transport, a persistent
reference registry, pronunciation preparation, and two Spanish-language Studio
interfaces. It does not train a model, ship weights, or include anyone's voice.

**License boundary:** original integration code/tests/Studio assets are MIT.
Upstream OmniVoice code is Apache-2.0 (copyright 2026 Xiaomi Corp.). The
[official model card](https://huggingface.co/k2-fsa/OmniVoice) states that the
pretrained model is **CC-BY-NC**, because of training-data restrictions. Do not
infer commercial model rights from this integration's MIT license. The card
does not specify a CC license version; clarify exact terms with upstream before
any redistribution or commercial use. No weights or model-data assets are
redistributed here. See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).


## Privacy, consent and deployment

Never clone someone without informed permission, impersonate a third party,
commit reference audio/transcripts, or use the model for fraud. Clearly disclose
synthetic speech where appropriate. MIT applies to software, not identity rights
or upstream model commercial rights. References and transcripts persist locally;
the browser retains only the chosen voice ID in local storage. Delete that browser
storage on shared machines. No consent enforcement is implemented in software.

Bind to loopback. Remote access requires an authenticated TLS proxy protecting
**all routes including WebSockets**, firewalling, upload/request/concurrency
limits and explicit allowed hosts. This project supplies none of those identity
or rate-limit controls. Browser same-origin and Host validation are only defense
in depth. Do not directly bind to an untrusted network. See [SECURITY.md](../SECURITY.md).

## Development

```bash
python -m pytest -q
python -m pip install build
python -m build
```

CI runs model-free tests, packaging, and an isolated mock wheel smoke. No weights,
voices, generated audio, private deployment scripts, secrets or Git history are
included in the release. Contributions: [CONTRIBUTING.md](../CONTRIBUTING.md).
