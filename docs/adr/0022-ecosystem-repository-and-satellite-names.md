# ADR 0022: The ecosystem repository, and the names beside this line

**Status:** accepted

## Context

[ADR 0018](0018-capability-placement-rule.md) decided *what* leaves this repository — a capability that needs
a dependency core will not adopt, carries policy, or has its own release cadence is a **package there** — and
left the identity of "there" to this record. The plans spelled it `xyberos/xyberos`, inferred from the
repository URL the published 1.x core declares in its own metadata.

The inference named the wrong repository in the state this ADR records, and the difference is not cosmetic:

| | `xyberos/xyberos` | `xyberos/xyberos-plugins` |
| --- | --- | --- |
| What it holds | the 1.x core line: `xyberos/`, `xyberos_cli/`, `xyberos_plugin_sdk/`, `xyberos_plugin_validator/`, `docs/`, `mkdocs.yml` | one directory per satellite distribution, each a standalone package with its own `pyproject.toml`, version, README, tests, and a top-level import root of its own (`xyberos_db`, `xyberos_mcp`) |
| What it publishes | the core distribution, from `.github/workflows/pypi-publish.yml`, authenticated with `PYPI_API_TOKEN` | the satellites, from `.github/workflows/pypi-plugins.yml`, which holds no token |
| What its versions say | the 1.x core line | `xyberos-db` `0.1.2` and `xyberos-mcp` `0.2.2` — the versions [the release guide](../release.md) already quotes |

A package index is unforgiving about this. A PyPI trusted publisher binds to a (repository, workflow,
environment) triple, so a repository that is deleted, re-created, or renamed invalidates the publisher for
every name it published, and each of those projects then has to be re-registered by whoever owns it.
`pypi-plugins.yml` states its own triple in the file, as the instruction a maintainer needs: repository
`xyberos-plugins`, workflow `pypi-plugins.yml`, environment blank.

That repository is under the project's control, so ADR 0018's rule and [the plan](../implementation.md)'s
publication decision point the same way: keep it, update it, and do not build a second home beside it.

## Decision

**The ecosystem repository is `xyberos/xyberos-plugins`, and it is updated in place rather than re-created.**

- **Name, owner, and URL.** `xyberos/xyberos-plugins`, in the `xyberos` organisation that already owns the
  `xyberos-*` names, at `https://github.com/xyberos/xyberos-plugins`, default branch `master`. At the time
  of this decision, `xyberos/xyberos` was the separate 1.x codebase, not the ecosystem repository; it has
  since been renamed to `xyberos/xyberosv1.0-deprecated`.
- **One repository, several distributions, grouped by subject.** One directory per subject and one directory per
  distribution inside it, each distribution with its own `pyproject.toml`, version, and changelog, sharing one CI
  matrix, one review path, one release procedure, and one drift job. That is the layout the placement rule
  assumes as the home of a *package*, and the repository already runs a flat version of it.
- **A subject folder owns its providers, and a 1.x tree stays only where a patch still needs it.** `db/` takes
  `xyberos-postgres` and any later database provider, `storage/` takes `xyberos-storage-s3` and any later
  storage provider, and `llm-providers/` takes `xyberos-openai-compatible` and any later model provider, one
  directory per distribution inside each. A **retired** name keeps its 1.x tree and moves down one level, so
  `db/xyberos_db/` still builds the `0.1.3` pointer patch a pinned user needs. A **reused** name does not: the
  rewrite becomes the source in the folder the name already had (`mcp/`, `auth/`, `observability/`), because a
  rewrite is not a patch and a second tree under the same distribution name would be two answers to one
  question. The published 1.x release stays on the index and the 1.x source stays in the repository's history.
- **The repository keeps its name and the publishing workflow keeps its filename**, because both are part of
  every publisher binding. Adding a directory, adding a version, and adding a matrix leg are free; renaming
  either one is not.
- **Tag addressing stays as the repository already runs it, one level deeper:** `vX.Y.Z` publishes every
  distribution, `<subject>/<distribution>/vX.Y.Z` publishes one, and `<subject>/vX.Y.Z` publishes a subject's
  distributions. The `<distribution>-v<version>` scheme the plan drafted is superseded by the convention in
  service.
- **The manifest stays in this repository.** [`packages.toml`](../../packages.toml) records every name beside
  this line, and it lives here because the documents checked against it are here — the feature matrix, the
  plugin catalogue, the release guide, [`tests/test_packages_manifest.py`](../../tests/test_packages_manifest.py),
  and [`tools/ecosystem.py`](../../tools/ecosystem.py), which the compatibility job reads rather than repeating
  the list in the ecosystem.

**Two names are reused, and each meets five conditions.** A reused name is a rewrite rather than a shim; it
declares `xyberos>=2,<3`; the old version stays published with the break stated in its README's first line;
exactly one publishing path owns the name; and its subject is not already answered by core or by an extra.

| Name | What the 2.x release carries | What the 1.x release keeps |
| --- | --- | --- |
| `xyberos-mcp` | the server direction: `expose()`, and a stdio transport if the owner approves one | `0.2.2` stays published and unedited. The client direction stays the core module `xyberos.mcp`, so one name answers one question instead of two |
| `xyberos-auth` | verification only: an assertion from a shared secret or a JWKS, and a `Principal` | `0.1.2` stays published, and the OAuth2 flows, OIDC, and the Auth0/Okta/Entra presets do not return. The framework still owns no identity model |

**Two names are retired, with a pointer rather than a shim.** Both capabilities already answer from this
repository, so a second distribution under the old name would be a second answer to one question.

| Retired name | Points at | Patch |
| --- | --- | --- |
| `xyberos-db` | `xyberos[database]` and the provider seam | `0.1.3` |
| `xyberos-metrics` | [`xyberos.http.RequestMetricsMiddleware`](../http.md) | none — the name has no published release to point from |

`xyberos-db`'s patch is metadata-only: the description and the README name the replacement, and the declared
`xyberos>=1.0,<2` pin stays, so nothing moves under a 1.x user. `xyberos-metrics` is the same decision with
nothing to retire: it does not resolve on the index, while `xyberos-db`, `xyberos-auth`, `xyberos-storage`, and
`xyberos-observability` all do, and it is not one of the twenty-three directories the ecosystem repository
holds. Publishing a patch for it would create the name rather than retire it, and the name would then advertise
a capability that ships in core. No shim ships, and no 2.x release is cut under either name.

**The other twenty satellite names stay where they are**, on the 1.x line under the repin they already shipped.
Reusing a name is a per-name decision that has to meet the five conditions above, not a sweep of an ecosystem.

**This supersedes part of [ADR 0017](0017-release-identity-and-lineage.md).** ADR 0017's lineage decision stands,
and so does its decision that the 1.x line stays published and installable. What this ADR replaces is its
treatment of the satellite line as a whole that stays untouched: for `xyberos-mcp` and `xyberos-auth`, the name
is decided individually.

## Consequences

- **One publishing path owns every `xyberos-*` name**, the retired pointer patches included, because the
  patches are released from the same repository as the names they retire. Nothing has to be re-registered on the
  index, because nothing moved.
- **The repository name and the workflow filename are now load-bearing.** Any future reorganisation of the
  organisation has to keep both, or accept re-registering a publisher for every published name.
- **A folder name is not a distribution name.** `db/` is the database subject; `db/xyberos_db/` and
  `db/xyberos_postgres/` are the distributions inside it. Where a new package lands, and whether it reuses a 1.x
  name at all, is settled per name under the five conditions, but the subject decides the folder.
- **The publishing workflow changes before the first nested distribution ships.** The ecosystem repository's
  `pypi-plugins.yml` enumerates the top-level directories from a hardcoded list and builds one distribution per
  entry, so nesting needs discovery of the `pyproject.toml` files, the tag patterns above, and a
  `working-directory` that can be one or two levels deep. Its identity does not change: the trusted publishers
  bind to the repository and to that workflow's filename, and both stay.
- **`xyberos-metrics` retires a name that was never published.** It has no directory in the ecosystem
  repository and no release on the index, so there is nothing to point *from* and no folder to create for it.
  The capability ships here, as `xyberos.http.RequestMetricsMiddleware`, and the name stays unused. A folder
  for it would exist only to claim a name no capability needs.
- **A name is `published` only when a check this repository can run proves it.** `packages.toml` records a
  `conformance` snippet for every published entry, and refuses a published entry without one, so the gate is
  what a package can be *checked* against rather than what it was tested with. The snippet has two shapes: a
  package implementing a seam core ships a suite for runs that suite — `xyberos-postgres`, `xyberos-storage-s3`,
  and `xyberos-openai-compatible` do — and one implementing no such seam imports its own public names against
  the core it declares and asserts that the core is this line, which is what `xyberos-mcp`, `xyberos-auth`,
  `xyberos-templates`, and `xyberos-observability` do. Their own tests prove them in their own repository, and
  a wheel installed from the index carries none of those, so the self-check is the weaker thing the
  compatibility job *can* run — and it is the check that fails when the installed core predates a module the
  package imports.
- **The plan's repository reference was inferred from the core's metadata and is corrected here.** The
  correction is [the implementation plan](../implementation.md)'s; this record is what it points at.
- **0021 stays unwritten.** This record takes the number the plans already use for it, and 0021 remains
  reserved by the plan for the deferred parallel-fan-out decision, so the index shows a gap until that decision
  is taken. Numbers are assigned when an ADR is written rather than reserved in advance
  ([the index](README.md)).
- **Reversing the placement takes a new ADR**, as ADR 0018 requires of any placement it records.
