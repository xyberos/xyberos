---
title: Security boundaries
status: verified
---

# Security boundaries

This page is short on guarantees on purpose. Most of what makes an application secure is decided
outside the framework — the proxy, the identity provider, the database's own permissions — and the
useful thing a framework can do is hold a small number of boundaries precisely and say clearly which
ones are not its business.

## The boundaries, measured

<!-- snippet: examples/learn_production/security01_boundaries.py -->

<!-- output: security01_boundaries -->
```text
a value that is the wrong type: ConfigurationError: app.debug must be a boolean
a setting the runtime does not know: ConfigurationError: unknown setting(s) at app: signing_key
a configuration file that is not there: ConfigurationError: configuration file does not exist: <cwd>/nowhere.toml
import xyberos pulls in: none
and the plugin API this runtime supports: 1
a plugin for another API: PluginCompatibilityError: plugin 'audit' targets plugin API '2', but this runtime supports '1'
response body: {'error': {'type': 'InternalServerError', 'message': 'the request could not be completed'}}
and the log, which the operator sees: [('unhandled error while serving a request', 'upstream refused the token sk-live-0123456789')]
```

Six boundaries, one line each:

### 1. A configuration failure names the setting, never the value

`app.debug must be a boolean` and `unknown setting(s) at app: signing_key` — the *second* one is the
interesting case, because a signing key is exactly the value that must not appear in a startup log. The
runtime refuses a key it does not know by name and prints nothing about what the value was; the same
holds for `plugins.<name>` sections, where an unknown key is refused with the key's name only
([the plugins page](../extend/plugins.md) has that refusal verbatim).

It is worth being precise about what this does *and does not* buy. It buys: a misspelling is a failed
start rather than a silently ignored setting, and no configuration *value* is ever echoed by the
runtime's own errors. It does not buy: secrets in the environment are still visible to anything that
can read the process, and `Settings.load` still holds them in memory. Secrets belong in a manager, and
[the security reference](../reference/security.md#secrets) is where that is argued.

### 2. Importing the framework imports no adapter

`import xyberos pulls in: none`, measured in a fresh interpreter against `sqlalchemy`, `aiosqlite`,
`alembic`, `starlette`, and `httpx`. The core runtime is the dependency-injection container, the
lifecycle, routing, settings, and the error taxonomy; every capability that needs a third-party package
lives behind an extra, and the import that needs it wraps the failure so a missing package comes back
as *install this extra* rather than a bare `ModuleNotFoundError`
[the extras
module](https://github.com/xyberos/xyberos/blob/master/src/xyberos/_extras.py) is the lookup table).

The security consequence is supply chain: a deployment that composes an application without the
`database` extra does not merely *not use* a driver, it does not have one installed to be exploited,
and an unused optional dependency cannot be the vulnerable one.

### 3. A plugin written for another API is refused by name, before it runs

`plugin 'audit' targets plugin API '2', but this runtime supports '1'`. A plugin declares `name`,
`api_version`, and `config_type`, and all three are checked *before* a line of the plugin executes. This
is compatibility, not protection: a plugin is trusted code
([ADR 0007](../reference/adr/0007-trusted-plugins.md)), the refusal exists so a version mistake is a
startup failure rather than a partially applied registration.

### 4. An error that is not an `HttpError` never reaches the client

The two lines at the end of the transcript are one rule with two audiences:

```text
response body: {'error': {'type': 'InternalServerError', 'message': 'the request could not be completed'}}
the log:       [('unhandled error while serving a request', 'upstream refused the token sk-live-0123456789')]
```

The client learns that the request failed and *nothing else*; the operator gets the message and the
traceback. The reverse rule matters just as much: an `HttpError` and its subclasses are the *only*
errors whose message is exposed, so a status code and a message a client can act on are a deliberate
choice in the handler, not an accident of what was raised.

### 5. What the framework does not do, said once

| Concern | Who owns it | Where it is argued |
| ------- | ----------- | ------------------ |
| TLS, CORS, header limits, body size, rate limits | the ASGI server and the proxy | [security reference](../reference/security.md) |
| Authentication | your identity provider and proxy | [the identity lesson](../learn/traditional/08-identity.md) |
| Session state and CSRF | `xyberos.http` middleware you pass, over a store you own | [the sessions example](https://github.com/xyberos/xyberos/tree/master/examples/sessions) |
| Assertion-header hardening | the proxy must **strip** what a client sends | the same lesson, and it is the lesson's own warning |
| Authorization | application code, at the edge, per request | [the hybrid path's principal lesson](../learn/hybrid/02-principal.md) |
| Secret storage and rotation | a secret manager | [security reference](../reference/security.md#secrets) |
| Prompt injection and model output trust | application code, with an allowlist and a schema | [the AI security lesson](../learn/ai/17-security.md) |
| Row-level authorization in the database | application code and the database | [the database reference](../reference/database.md) |
| Auditing who did what | application code, in the transaction it describes | [the hybrid path's audit lesson](../learn/hybrid/03-audit.md) |

### 6. The two boundaries this page will not claim

- **There is no sandbox.** A plugin, a provider, or a model tool runs with the privileges of the
  process. "Trusted" is the whole of the guarantee, and it is why nothing can become a plugin by being
  installed: `app.add_plugin(...)` is the only way in.
- **There is no tenancy model.** A tenant is an application concept, and the framework's contribution is
  that its request scope gives you one place to put the principal — not that it enforces anything.

## A review checklist

What to check before a deployment, in the order the mistakes usually happen:

1. **`xyberos check` shows the configuration you meant**, including `environment` and `debug`.
2. **Every claim in the model's output is validated before it is used**, and every tool the model may
   call is behind an allowlist ([the AI tools lesson](../learn/ai/11-tools.md)).
3. **No `HttpError` subclass carries internal detail in its message** — a mapped message is public by
   definition.
4. **The proxy strips the headers it sets**, including `X-Request-ID` and any identity assertion.
5. **Internal errors are logged with their traceback** and the log sink is not the client's response
   body ([observability](observability.md)).
6. **Secret material is not in the image, the repository, or a command line** — `migrate --url` redacts,
   `ps` does not.
7. **The dependencies you do not use are not installed**, which is what the extras are for.
8. **A failure in authorization is a refusal, not a bypass** — the lesson's rule: a missing secret makes
   every request `401`.

## Common mistakes

- **Logging request bodies to debug an integration.** Bodies contain whatever the client sent, including
  credentials; log identifiers and outcomes instead.
- **Trusting a model's output because it parsed.** Structured output buys you a shape, not a
  permission; validate against the domain and authorize separately.
- **Adding a `middleware=` entry that rewrites errors into the framework's own mapping.** Order matters:
  your middleware runs inside the request scope and after error mapping
  ([observability](observability.md) has the stack), so an error you raise there is mapped, and an error
  you swallow there is gone.
- **Treating the `type` field in an error body as sensitive.** It is the exception's class name and it is
  designed to be readable; the message is where restraint applies.
