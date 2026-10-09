# Security policy

This is a local, single-operator research integration, not a multi-tenant service.
Bind Uvicorn to 127.0.0.1. There is no built-in authentication, authorization,
quota system, or tenant isolation. Host validation and same-origin browser
checks are defense in depth, not authentication. Clients without Origin headers
are permitted. Never expose the service directly to the Internet or an untrusted
LAN. For remote access, use an authenticated TLS reverse proxy that protects
**every** HTTP and WebSocket route, rate/body/concurrency limits, a host allowlist,
and a firewall. Only trust forwarded headers from that proxy.

Uploads have an extension allowlist and a byte cap; filename-derived paths are
not used. Formats must also be decodable by the upstream model/audio libraries;
an allowed extension does not prove valid or safe audio. Bound multipart request
sizes at the proxy as parsing occurs before the application upload limit.
References are private on-disk biometric data, not served as static assets.
Caller-provided local reference paths are denied at REST boundaries. Registry
warming checks resolved containment under the upload root. Client errors are
bounded messages; keep server logs private. Run as an unprivileged account with
an operator-only upload directory. Local administrators/file-system writers are
trusted; symlink races by a malicious local account are outside this boundary.

Use one worker and serialize operator registration operations. The JSON registry
is not a transactional multi-process database; simultaneous writes can lose
updates. Generation may queue behind the model lock and cancel only discards
pending text: it does not interrupt a running model call. Protect against denial
of service with external request/text/time limits. Failed clones may leave a
reference file; review and delete unused private files. No automatic expiry or
delete API is provided. To revoke a voice, stop the server, remove its registry
entry and associated reference, then restart to clear memory caches. Do not
commit real voices, transcripts, logs, tokens, or weights.

Report vulnerabilities privately to the maintainer through a private contact
channel or the hosting platform's private security advisory feature when
enabled. Do not include real reference audio, personal transcripts, secrets,
or filesystem paths in public issues. No security-response SLA is promised.
