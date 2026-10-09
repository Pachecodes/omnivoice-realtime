# Third-party notices and license boundaries

## Integration versus model

Jesús Pacheco / Akitá authored this repository's integration, not OmniVoice.
Upstream: https://github.com/k2-fsa/OmniVoice (k2-fsa); package author: Han Zhu.
Upstream code license: Apache-2.0, copyright 2026 Xiaomi Corp. A copy of the
upstream license is included in `licenses/OmniVoice-Apache-2.0.txt`. The adapter
imports upstream interfaces; no model implementation or weight files are bundled.

The official model card at https://huggingface.co/k2-fsa/OmniVoice states:
“Our code is released under the Apache 2.0 License. The pre-trained model is
licensed under the CC-BY-NC due to constraints from its training data (e.g., Emilia).”
It does not specify a CC version and no separate model LICENSE file was available
at review. Treat the pretrained model as **noncommercial**, clarify exact terms
with upstream for any redistribution, and do not infer model rights from MIT or
Apache code licenses. No model, dataset, reference voices or generated audio are
redistributed by this repository. Optional runtime downloads have separate terms.
The model card identifies Qwen/Qwen3-0.6B as base model; the selected ASR is
openai/whisper-small. Those models and training-data licenses remain independent.

Citation (upstream model research):

```bibtex
@article{zhu2026omnivoice,
  title={OmniVoice: Towards Omnilingual Zero-Shot Text-to-Speech with Diffusion Language Models},
  author={Zhu, Han and Ye, Lingxuan and Kang, Wei and Yao, Zengwei and Guo, Liyong and Kuang, Fangjun and Han, Zhifeng and Zhuang, Weiji and Lin, Long and Povey, Daniel},
  journal={arXiv preprint arXiv:2604.00688},
  year={2026}
}
```

## Dependency license review

These are independently installed dependencies, not code incorporated under MIT.
Publisher-maintained PyPI metadata was queried for the following packages during
release preparation. This table is a discovery review, not a claim that optional
model dependencies were installed or their complete transitive closure audited.
Resolved environments/platform wheels can include additional components and
licenses; preserve their distribution notices when redistributing an environment.

| Package | Metadata version checked | Publisher-declared license | Authoritative metadata |
| --- | --- | --- | --- |
| fastapi | 0.143.0 | MIT | [PyPI](https://pypi.org/pypi/fastapi/json) |
| uvicorn | 0.54.0 | BSD-3-Clause | [PyPI](https://pypi.org/pypi/uvicorn/json) |
| pydantic | 2.14.0 | MIT | [PyPI](https://pypi.org/pypi/pydantic/json) |
| numpy | 2.5.3 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | [PyPI](https://pypi.org/pypi/numpy/json) |
| soundfile | 0.14.0 | BSD 3-Clause License | [PyPI](https://pypi.org/pypi/soundfile/json) |
| python-multipart | 0.0.32 | Apache-2.0 | [PyPI](https://pypi.org/pypi/python-multipart/json) |
| anyio | 4.15.1 | MIT | [PyPI](https://pypi.org/pypi/anyio/json) |
| pytest | 9.1.1 | MIT | [PyPI](https://pypi.org/pypi/pytest/json) |
| httpx | 0.28.1 | BSD-3-Clause | [PyPI](https://pypi.org/pypi/httpx/json) |
| setuptools | 84.0.0 | MIT | [PyPI](https://pypi.org/pypi/setuptools/json) |
| build | 1.6.1 | MIT | [PyPI](https://pypi.org/pypi/build/json) |
| omnivoice | 0.2.1 | Apache-2.0 | [PyPI](https://pypi.org/pypi/omnivoice/json) |
| accelerate | 1.15.0 | Apache | [PyPI](https://pypi.org/pypi/accelerate/json) |
| gradio | 6.30.0 | Apache-2.0 | [PyPI](https://pypi.org/pypi/gradio/json) |
| librosa | 1.0.0 | ISC | [PyPI](https://pypi.org/pypi/librosa/json) |
| pydub | 0.25.1 | MIT | [PyPI](https://pypi.org/pypi/pydub/json) |
| tensorboardx | 2.6.5 | MIT | [PyPI](https://pypi.org/pypi/tensorboardx/json) |
| torch | 2.14.1 | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT | [PyPI](https://pypi.org/pypi/torch/json) |
| torchaudio | 2.11.0 | License :: OSI Approved :: BSD License | [PyPI](https://pypi.org/pypi/torchaudio/json) |
| transformers | 5.19.0 | Apache 2.0 License | [PyPI](https://pypi.org/pypi/transformers/json) |
| webdataset | 1.0.2 | BSD-3-Clause | [PyPI](https://pypi.org/pypi/webdataset/json) |
| starlette | 1.7.0 | BSD-3-Clause | [PyPI](https://pypi.org/pypi/starlette/json) |
| cffi | 2.1.1 | MIT-0 | [PyPI](https://pypi.org/pypi/cffi/json) |
| websockets | 17.2 | BSD-3-Clause | [PyPI](https://pypi.org/pypi/websockets/json) |
| uvloop | 0.23.0 | MIT License | [PyPI](https://pypi.org/pypi/uvloop/json) |
| httptools | 0.8.0 | MIT | [PyPI](https://pypi.org/pypi/httptools/json) |
| watchfiles | 1.3.0 | MIT | [PyPI](https://pypi.org/pypi/watchfiles/json) |
| python-dotenv | 1.2.4 | BSD-3-Clause | [PyPI](https://pypi.org/pypi/python-dotenv/json) |
| pyyaml | 6.0.3 | MIT | [PyPI](https://pypi.org/pypi/pyyaml/json) |

SoundFile binary wheels bundle **libsndfile**, which is LGPL-2.1-or-later;
SoundFile's BSD Python license does not replace that license. See
https://github.com/libsndfile/libsndfile/blob/master/COPYING and the installed
wheel's notices. NumPy and PyTorch wheels also carry bundled-component licenses;
use the exact wheel's license texts, not only the headline Python-package license.
No external fonts/images, CDN libraries or audio assets are bundled in the Studio;
the shipped HTML/CSS/JavaScript are integration assets.

Review anchors: OmniVoice GitHub master commit
`08be0b4ccbac3e13e374e86fbfead4b4cac343e2`; model card revision
`c5fdb5ccb189668d56333f77ba2629f4cd7535f4`; PyPI OmniVoice 0.2.1 metadata
https://pypi.org/pypi/omnivoice/0.2.1/json. Terms can change upstream; re-check
before changing model versions or redistributing third-party assets.

## Exact CPU/mock wheel environment

The following publisher metadata was also checked at the exact versions
installed for wheel verification (includes the HTTP smoke client). Optional
model/ASR dependency closures were not installed or audited.

| Package | Version | License | Authoritative metadata |
| --- | --- | --- | --- |
| uvicorn | 0.54.0 | BSD-3-Clause | [PyPI](https://pypi.org/pypi/uvicorn/0.54.0/json) |
| websockets | 17.2 | BSD-3-Clause | [PyPI](https://pypi.org/pypi/websockets/17.2/json) |
| watchfiles | 1.3.0 | MIT | [PyPI](https://pypi.org/pypi/watchfiles/1.3.0/json) |
| soundfile | 0.14.0 | BSD 3-Clause License | [PyPI](https://pypi.org/pypi/soundfile/0.14.0/json) |
| click | 8.5.0 | BSD-3-Clause | [PyPI](https://pypi.org/pypi/click/8.5.0/json) |
| uvloop | 0.23.0 | MIT License | [PyPI](https://pypi.org/pypi/uvloop/0.23.0/json) |
| opentelemetry-api | 1.45.1 | Apache-2.0 | [PyPI](https://pypi.org/pypi/opentelemetry-api/1.45.1/json) |
| numpy | 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | [PyPI](https://pypi.org/pypi/numpy/2.4.6/json) |
| httpcore | 1.0.9 | BSD-3-Clause | [PyPI](https://pypi.org/pypi/httpcore/1.0.9/json) |
| httptools | 0.8.0 | MIT | [PyPI](https://pypi.org/pypi/httptools/0.8.0/json) |
| h11 | 0.16.0 | MIT | [PyPI](https://pypi.org/pypi/h11/0.16.0/json) |
| python-multipart | 0.0.32 | Apache-2.0 | [PyPI](https://pypi.org/pypi/python-multipart/0.0.32/json) |
| PyYAML | 6.0.3 | MIT | [PyPI](https://pypi.org/pypi/PyYAML/6.0.3/json) |
| fastapi | 0.143.0 | MIT | [PyPI](https://pypi.org/pypi/fastapi/0.143.0/json) |
| pydantic | 2.14.0 | MIT | [PyPI](https://pypi.org/pypi/pydantic/2.14.0/json) |
| python-dotenv | 1.2.4 | BSD-3-Clause | [PyPI](https://pypi.org/pypi/python-dotenv/1.2.4/json) |
| cffi | 2.1.1 | MIT-0 | [PyPI](https://pypi.org/pypi/cffi/2.1.1/json) |
| certifi | 2026.7.22 | MPL-2.0 | [PyPI](https://pypi.org/pypi/certifi/2026.7.22/json) |
| annotated-types | 0.8.0 | MIT | [PyPI](https://pypi.org/pypi/annotated-types/0.8.0/json) |
| annotated-doc | 0.0.5 | MIT | [PyPI](https://pypi.org/pypi/annotated-doc/0.0.5/json) |
| typing-inspection | 0.4.4 | MIT | [PyPI](https://pypi.org/pypi/typing-inspection/0.4.4/json) |
| starlette | 1.7.0 | BSD-3-Clause | [PyPI](https://pypi.org/pypi/starlette/1.7.0/json) |
| httpx | 0.28.1 | BSD-3-Clause | [PyPI](https://pypi.org/pypi/httpx/0.28.1/json) |
| pydantic_core | 2.50.0 | MIT | [PyPI](https://pypi.org/pypi/pydantic_core/2.50.0/json) |
| typing_extensions | 4.16.0 | PSF-2.0 | [PyPI](https://pypi.org/pypi/typing_extensions/4.16.0/json) |
| pycparser | 3.1 | BSD-3-Clause | [PyPI](https://pypi.org/pypi/pycparser/3.1/json) |
| anyio | 4.15.1 | MIT | [PyPI](https://pypi.org/pypi/anyio/4.15.1/json) |
| idna | 3.20 | BSD-3-Clause | [PyPI](https://pypi.org/pypi/idna/3.20/json) |

