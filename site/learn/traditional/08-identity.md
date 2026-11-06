---
title: Identity from upstream
path: traditional
lesson: 8
tier: not-provided
status: verified
verify: output
example: examples/learn_traditional/traditional08_identity.py
prerequisites: ["/learn/traditional/07-migrations"]
---

# Lesson 8 — identity from upstream

## What you will build

The first lesson about something a request carries that the application must not trust. Xyberos ships no
identity, tenancy, or authorization model and will not
([ADR 0014](../../reference/adr/0014-no-identity-or-authorization-model.md)), so this lesson is not
about a framework feature: it is about the *shape* the ADR sanctions, and the four rules that make it
safe. Sessions **do** ship now, as middleware the application passes
([ADR 0024](../../reference/adr/0024-sessions-and-csrf-are-middleware-in-the-http-module.md)), and this
lesson keeps them out of the identity path deliberately: a session remembers state, never who somebody
is.

Two of the endpoints you already have are the wrong way round for this. `GET /users/{user_id}` asks the
caller to name a user; after this lesson the caller cannot name one at all.

## What you need

Nothing new. The interesting part of this lesson is what it does *not* install: no auth library, no
role model, and no *durable* session store. `xyberos.http.SessionMiddleware` ships, and
[the sessions example](https://github.com/xyberos/xyberos/tree/master/examples/sessions) is what it
is for; deciding who the caller is stays outside it.

## The four rules

| Rule | What it means here |
| ---- | ------------------ |
| A header is trusted only because something **verified** it | `PrincipalVerifier` re-computes an HMAC over the subject and roles; a header that merely arrived proves nothing |
| The verified principal is passed **as an argument** | every `/me` service call takes a `Principal`, so there is no code path that reaches a user without one |
| The subject never comes from the **payload** | `PATCH /me` refuses `id`, `enabled`, and `external_subject`: the client does not get to say who it is |
| Context values are **not** identity | `bind_context` is diagnostic only ([security guide](../../reference/security.md)); a subject in `contextvars` is ambient authority |

`examples/user_management/identity.py` is the whole verifier. Everything else in this lesson follows
from it:

<!-- snippet: examples/user_management/identity.py -->

Note what the secret does when it is missing. A deployment with no `XYBEROS_IDENTITY_SECRET` refuses
every request with a `401` rather than trusting one, and it fails closed *without crashing*: the
verifier is constructed at import time and asks the question on the first request.

## The link is a migration

A verified principal is a fact about the caller, not an account. Linking the two needs somewhere to keep
the link, and that is lesson 7's machinery doing its job: a new column, nullable and unique, following
the revision that created the table.

<!-- snippet: examples/user_management/migrations/versions/0002_add_external_subject.py -->

Two decisions are recorded in that file. The subject is a **separate column** rather than the email
address, because an email is what a person may change and a subject is what the identity provider will
keep asserting; and the column is **unique**, so two accounts cannot claim one subject even if two
requests race past the same check.

## Where the principal goes

`examples/user_management/app.py` gains a provider for the verifier and three routes. Each one verifies
first, then calls the service with the principal — never with a user id:

<!-- snippet: examples/user_management/app.py -->

`UserService` grew the methods those routes call: `find_own_user(principal)` and
`update_own_profile(principal, changes)`. Neither has a `user_id` parameter. That is the design in one
sentence: the caller cannot ask for an account, only for *its* account, and the query that finds it is
`WHERE external_subject = :subject` from the principal.

`create_user` gained one keyword argument — `external_subject` — so `POST /me` reuses every rule lesson 4
established: the same email validation, the same duplicate check, the same transaction. A repeat claim
is a `409` decided *before* the payload is judged, because the conflict is about the request's target
rather than about the body.

## What the lesson runs

<!-- snippet: examples/learn_traditional/traditional08_identity.py -->

## How to run it

=== "PowerShell"

    ```powershell
    $env:PYTHONPATH = "src;examples"
    python -m learn_traditional.traditional08_identity
    ```

=== "POSIX"

    ```bash
    PYTHONPATH=src:examples python -m learn_traditional.traditional08_identity
    ```

## What it prints

<!-- output: traditional08_identity -->
```text
no secret configured -> 401 {'error': {'type': 'UnauthenticatedError', 'message': 'the request is not authenticated: no identity secret is configured in XYBEROS_IDENTITY_SECRET'}}
unsigned -> 401 {'error': {'type': 'UnauthenticatedError', 'message': 'the request is not authenticated: X-Authenticated-Subject is required'}}
signed for the wrong roles -> 401 {'error': {'type': 'UnauthenticatedError', 'message': 'the request is not authenticated: the assertion signature does not match'}}
before claiming an account -> 404 {'error': {'type': 'AccountNotLinkedError', 'message': 'no local account is linked to ada@idp'}}
claim -> 200 {'id': 1, 'email': 'ada@example.com', 'display_name': 'Ada Lovelace', 'enabled': True, 'external_subject': 'ada@idp'}
read back -> 200 {'id': 1, 'email': 'ada@example.com', 'display_name': 'Ada Lovelace', 'enabled': True, 'external_subject': 'ada@idp'}
claim again -> 409 {'error': {'type': 'AccountAlreadyLinkedError', 'message': 'ada@idp is already linked to an account'}}
PATCH /me {'display_name': 'Ada,   Countess of Lovelace '} -> 200 {'id': 1, 'email': 'ada@example.com', 'display_name': 'Ada, Countess of Lovelace', 'enabled': True, 'external_subject': 'ada@idp'}
PATCH /me {'enabled': False} -> 422 {'error': {'type': 'UserValidationError', 'message': 'unknown field: enabled'}}
PATCH /me {'external_subject': 'linus@idp'} -> 422 {'error': {'type': 'UserValidationError', 'message': 'unknown field: external_subject'}}
PATCH /me {'id': 2} -> 422 {'error': {'type': 'UserValidationError', 'message': 'unknown field: id'}}
somebody else -> 404 {'error': {'type': 'AccountNotLinkedError', 'message': 'no local account is linked to linus@idp'}}
```

| Line | What it establishes |
| ---- | ------------------- |
| `no secret configured -> 401` | a deployment that forgot its secret refuses everything, and says why without quoting the secret |
| `unsigned -> 401` | headers alone are not identity: there is no signature to check |
| `signed for the wrong roles -> 401` | the signature covers the roles, so a caller cannot add one by editing a header |
| `before claiming an account -> 404` | being authenticated is not the same as having an account here |
| `claim -> 200` | the verified subject becomes `external_subject` on a row created by the same rules as lesson 4 |
| `claim again -> 409` | one subject, one account |
| `PATCH /me {enabled: False} -> 422` | a user does not get to enable or disable themselves |
| `PATCH /me {external_subject: ...} -> 422` | and does not get to re-point the link |
| `PATCH /me {id: 2} -> 422` | nor to name somebody else's account |
| `somebody else -> 404` | another verified subject has their own account, and sees nothing of this one |

## What the framework provides, and what it refuses to

| Provided | Refused |
| -------- | ------- |
| `HttpError` with the status you choose (`401` here, `403` in lesson 9) | any identity, role, or tenancy model |
| sessions and CSRF, as middleware the application passes ([ADR 0024](../../reference/adr/0024-sessions-and-csrf-are-middleware-in-the-http-module.md)) | a login form, a password store, or an authorization decision |
| request-scoped providers, if a verifier should cache its work inside one request | a tenant in `contextvars`, or any ambient authority |
| an error policy that never leaks an internal message to a client | enforcement of tenancy for you, or a warning when you forget to verify |

That list is short on purpose. A framework that owned authorization would be responsible for security it
cannot see, and a half-built one would be worse than none.

## Common mistakes

- **Trusting a header because it is present.** `X-Authenticated-Subject: ada@idp` is a string anyone can
  send. It becomes a fact only after something checked it, and the check is what this lesson's HMAC
  stands in for: replace it with a token signature or an introspection call.
- **Putting the principal in a session.** `xyberos.http.SessionMiddleware` ships
  ([ADR 0024](../../reference/adr/0024-sessions-and-csrf-are-middleware-in-the-http-module.md)), and a
  session is the right place for *state* — a cart, a chosen theme, a draft. It is the wrong place for
  *identity*: an assertion that arrives on every request should be verified on every request, and a
  cached principal is a second identity system with its own lifetime, revocation, and failure modes.
- **Scoping by a value from the payload.** A client that can name the account it reads is a client that
  can name somebody else's. `PATCH /me` refuses `id` and `external_subject` for exactly this reason.
- **Using `bind_context` as authorization.** It is for logs and correlation. Authorization decisions
  read the principal, which is an argument.
- **Forgetting to strip the assertion headers at the edge.** This is the one operational failure mode
  that turns this shape into a vulnerability: if the proxy forwards a client-supplied
  `X-Authenticated-Subject`, a client chooses their own subject. The proxy must remove these headers
  from inbound requests and set them only after authenticating. Xyberos does no header hardening for you
  ([security guide](../../reference/security.md)).

## Exercise

Write the test-side version: build the application, replace the verifier with one that answers from a
fixed subject using `app.with_overrides`, and claim and read an account **without any assertion headers
at all**. Then explain to yourself why that is a test affordance and not something to deploy.

<details>
<summary>Show the answer</summary>

<!-- snippet: examples/learn_traditional/traditional08_exercise.py -->

<!-- output: traditional08_exercise -->
```text
claimed with no headers: 200 ada@idp
read with no headers: 200 ada@example.com
```
</details>

## Next

Lesson 9 is the other half of the decision: what a *verified* principal may do. Roles, `401` against
`403`, and the deployment obligation that keeps an assertion from being forgeable at the edge.
