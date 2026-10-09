# Contributing

Use Python 3.11 or newer in an isolated virtual environment. Install `.[dev]`,
then run `python -m pytest -q`. Add regression tests first for security fixes;
mock tests must explicitly remain mock tests. Run `python -m build`, inspect the
wheel and sdist, and smoke-test an isolated wheel installation before submitting.

Keep integration changes separate from upstream model claims. Do not add model
weights, voice references, generated audio, private endpoints, secrets, data,
or logs. Use synthetic fixtures created at test time. Never download models in
CI. Changes to the upstream model API must name the version tested and say
whether genuine synthesis was exercised. Document protocol and security changes.

Contributions to original integration code are under this repository's MIT
license. Do not contribute third-party code/assets unless their provenance and
redistribution rights are documented. Model licenses and consent obligations
remain independent. File public bug reports with sanitized reproductions only.
