# Release guide

> Status: Phase 7. This page is the procedure for the first release and for every one after it, the
> deployment plan for the index it publishes to, and the audit results it rests on.

The project is at **`2.2.0`**, the third release of this line. The first release was `2.0.0`, because
the `xyberos` name was already held on the package index by the published 1.x line.
The versioning rules that make that the right number are in [the stability guide](./stability.md), and
the decision itself is [ADR 0017](./adr/0017-release-identity-and-lineage.md).

## What a release is, here

A release is a tag, an artefact, a changelog entry, and evidence that the artefact installs and runs.
Nothing is published automatically: the [release decision gate](./implementation.md#phase-7---developer-experience-hardening-and-release)
is signed off by the project owner first, and a release that fails an artefact check is not published
at all rather than published with a caveat.

## Before the tag

1. **Move the changelog.** `CHANGELOG.md` has an `Unreleased` section. Rename it to the version and
   date (`2.0.0` for the first release of this line), and open a new empty `Unreleased` section above
   it. The entry's first line states that `2.0.0` is not compatible with the published 1.x line, so a
   reader learns that before they read the features.
2. **Bump the version in all six places.** Two carry it — `version` in
   [pyproject.toml](../pyproject.toml) and `__version__` in
   [src/xyberos/\_\_init\_\_.py](../src/xyberos/__init__.py) — and four tests pin the version
   literally: `tests/test_package.py`, `tests/test_public_api.py`, `tests/test_compatibility.py`, and
   `tests/cli/test_cli.py`. The four pins are deliberate: they make the bump a reviewed diff instead
   of a silent string change, and they fail loudly when one of the first two is missed.
3. **Run the full gate.** From a clean environment:

   ```powershell
   python -m pip install -e ".[dev,http,database]"
   python -m pip install --no-deps -e tests/fixtures/metrics_plugin
   python -m pytest
   ruff check src tests examples
   ruff format --check src tests examples
   mypy
   python -m build
   ```

4. **Run the artefact checks.** `tests/test_release_artefacts.py` builds the wheel and sdist and
   asserts what they must contain, so step 3 already covers this. The assertions are about things
   that have gone wrong here before: missing `py.typed`, stale text embedded in `METADATA`, a licence
   file that does not ship, an entry point that is not declared, and paths that are wrong for a
   `src` layout.
5. **Run the clean-install smoke test**, which is the one check that must happen *outside* the
   checkout:

   ```powershell
   python -m build
   python -m venv .smoke
   .smoke\Scripts\python -m pip install dist\xyberos-<version>-py3-none-any.whl
   .smoke\Scripts\xyberos --version
   .smoke\Scripts\xyberos check
   .smoke\Scripts\xyberos new smoke --directory .
   .smoke\Scripts\xyberos check --app smoke.app:create_app --app-dir smoke\src
   .smoke\Scripts\python -m pip install "starlette>=0.40,<2" "httpx>=0.27,<1"
   .smoke\Scripts\xyberos check --app smoke.app:create_app --app-dir smoke\src
   ```

   The step before the extras are installed must fail with a message naming `xyberos[http]`; the step
   after must report `provider graph: valid` and a route count. That pair is the check that the
   optional-dependency story is true for an artefact, not only for a checkout. CI runs the same
   sequence in the `installed-artefact` job.

6. **Update what publication makes false — done for `2.0.0`.** This step existed because three places
   said the framework was not published: the prerequisites note in [the tutorial](./tutorial.md), the
   install section in [getting started](./getting-started.md), and the comment above the generated
   project's dependency in [src/xyberos/cli/scaffold.py](../src/xyberos/cli/scaffold.py). They now
   install from the index, and the step is a first-release step only: a later release has nothing to
   flip, because the framework stays published.
7. **Confirm the gate.** Every row of the release decision gate in
   [implementation.md](./implementation.md) has evidence, and the open owner decisions listed under
   "Remaining owner decisions" are either decided or explicitly deferred with a trigger.

## Dependency and licence audit

The framework's only unconditional requirement is `tomli` on Python 3.10, and the standard library's
`tomllib` above it. Everything else is an extra, and the closures below were computed from installed
distribution metadata rather than from the declarations alone, because a transitive dependency is
still a dependency. To reproduce one, install the extra into an empty environment and list what
arrived:

```powershell
python -m venv .audit
.audit\Scripts\python -m pip install -e ".[http,database]"
.audit\Scripts\python -m pip list
```

| Extra | Installed closure | Licences |
| --- | --- | --- |
| core | *(none beyond the package; `tomli` on 3.10)* | — |
| `http` | `starlette`, `httpx`, `anyio`, `certifi`, `h11`, `httpcore`, `idna`, `typing_extensions` | BSD-3-Clause, MIT, MPL-2.0, PSF-2.0 |
| `database` | `sqlalchemy`, `aiosqlite`, `alembic`, `Mako`, `MarkupSafe`, `greenlet`, `typing_extensions` | MIT, BSD-3-Clause, PSF-2.0 |
| `ollama` | `httpx`, `anyio`, `certifi`, `h11`, `httpcore`, `idna`, `typing_extensions` | BSD-3-Clause, MIT, MPL-2.0, PSF-2.0 |
| `durable` | the `database` closure | as `database` |

Every licence is permissive or weak-copyleft and compatible with distributing Xyberos under
Apache-2.0. Two details are worth knowing rather than assuming:

- **`certifi` is MPL-2.0**, a file-level copyleft. It is a transitive dependency of `httpx` and is not
  modified here, which is what MPL-2.0 requires; it is listed because it is the one licence in the
  set that is not permissive.
- **The floors are what move.** Every range has a floor, and only two have a ceiling
  (`sqlalchemy>=2.0,<2.1`, `httpx>=0.27,<1`, because the next major is where a breaking change lands).
  A newer release inside a range is reachable by resolution, so fixing a vulnerable dependency means
  moving its floor, not rewriting the cap.

There is no `NOTICE` file: nothing in the dependency set requires one, and Apache-2.0 requires it only
when the work itself carries notices.

### Software bill of materials

Xyberos does not generate an SBOM at build time, because an SBOM describes *an installed
environment*, not a wheel, and pinning one into the artefact would be a snapshot that goes stale
immediately. Generate it where the environment is known, with whatever supply-chain tooling the
deployment already uses — for example `pip install cyclonedx-bom` and
`cyclonedx-py environment --output-format json --outfile sbom.json` in the release environment — and
attach it to the release. The table above is the minimum evidence and is regenerated by the command
above.

## Publishing

1. Tag the commit `v<version>` and push the tag.
2. Attach the wheel, the sdist, and the SBOM to the release, with the changelog section as the
   release notes and the gate reference linking back to the evidence.
3. Verify the published artefact by installing *it* rather than the checkout, in a clean environment,
   one last time.

The upload itself, and the checks that only make sense once a release is on the index, are below.

## Deploying to PyPI

> Status: **performed, for `2.0.0` and `2.1.0`.** The index serves both — wheel and sdist — and this
> repository carries the `v2.0.0` tag with the changelog entry the upload used as its release notes, dated
> **2026-10-11**. The four preconditions above were met before the first run rather than during it, which is
> the order this section exists to insist on. The ecosystem followed: all eight distributions beside this line
> are published from [`xyberos/xyberos-plugins`](https://github.com/xyberos/xyberos-plugins), each against the
> core range it declares. [ADR 0017](./adr/0017-release-identity-and-lineage.md) still decides the number, and
> nothing here reopens it.

### Preconditions

The distribution name is not a choice to be made. `xyberos` is held on PyPI by this project's 1.x
line — 16 releases from `0.4.0` to `1.0.3`, the newest uploaded 2026-08-17 — and an index does not
re-register a name that has releases. The first upload is therefore not a new project but a release of
an existing one, which is why these four things come first.

| # | Precondition | Why it blocks | How to confirm |
| --- | --- | --- | --- |
| 1 | The trusted publisher on the PyPI project — **owner `xyberos`, repository `xyberos`, workflow `publish.yml`, environment left empty** | GitHub's repository rename does not update PyPI's OIDC publisher record. Update that record before the next release; a mismatch fails authentication, and there is no token fallback | Compare the registration against the table in [The publishing workflow](#the-publishing-workflow), including the empty environment |
| 2 | The repository this line publishes from — **`https://github.com/xyberos/xyberos`**, default branch `master` | The declared project URLs, the README's links, and a trusted publisher all bind to it, so the URL and the branch name have to be settled before the metadata is written | `git rev-parse master origin/master` matches, and every declared URL resolves — see [Preparing the repository](#preparing-the-repository) |
| 3 | The publication path — **trusted publishing from `.github/workflows/publish.yml`**, started by hand, with PyPI as its only destination | The run authenticates with an OIDC identity and keeps no secret, and it uploads straight to the index, so the publisher has to be correct before the first attempt rather than during it | See [The publishing workflow](#the-publishing-workflow) |
| 4 | The `Documentation` URL — **`https://docs.xyberos.com`, now serving this line's site**; the repository's `docs/` directory held until then | The domain was held by a **Cloudflare-hosted deployment of a stale 1.x build**, not by a GitHub Pages setting in either repository. It was deleted on **2026-10-12** and the domain was then attached to this line's own Cloudflare Worker, which is what `wrangler.jsonc` in this repository configures. The 1.x guides are maintained in [`xyberos/xyberosv1.0-deprecated`](https://github.com/xyberos/xyberosv1.0-deprecated) and their Pages URL follows that renamed repository | `curl -sI https://docs.xyberos.com/` answers `200` from a Cloudflare Worker serving this site — tabs in the markup, snippet includes fenced and labelled with their file, the site's own `404.html` for an unknown path, and `/roadmap/` reporting 54 of 54 lessons. The declared value in `[project.urls]` names it ([the documentation site plan](../site/implementation.md) records the order: Pages preview, then the domain, then the metadata) |

### Preparing the repository

The repository used for the first releases was `https://github.com/xyberos/xyberos2.0` and began empty;
it has since been renamed to `https://github.com/xyberos/xyberos`. The unrelated 1.x codebase was kept
separate and is now archived as
[`xyberos/xyberosv1.0-deprecated`](https://github.com/xyberos/xyberosv1.0-deprecated). The old URL
redirects to the renamed repository, and this line's history contains only its own commits — which is
what a provenance attestation describes.

| | |
| --- | --- |
| Repository | `https://github.com/xyberos/xyberos` (renamed from `xyberos2.0`) |
| Default branch | `master`, which is also the local branch and the one every declared link names |
| First push | `5ebef0a`, a normal push into an empty repository rather than a force push |
| Previous 1.x codebase | `https://github.com/xyberos/xyberosv1.0-deprecated`, preserved |

Two properties of that arrangement are load-bearing, and both are easy to undo by accident:

- **The branch name is load-bearing.** The README's links and the `Documentation` URL name `master`
  explicitly. Renaming the default branch to `main` later breaks all of them at once, and the project
  page keeps showing the links it can no longer resolve. (The `Documentation` URL is the one exception
  once it moves to this line's site — see [precondition 4](#preconditions) — but every README link
  still binds to this branch name.)
- **An empty repository is not a valid target for the declared URLs.** Until the first push lands, the
  `Repository`, `Issues`, and `Documentation` links and every link in the README resolve to a
  repository with no content, which is worse than declaring nothing at all. The push is part of
  preparing the release rather than an afterthought. All 38 URLs that the metadata and the long
  description declare were requested after the first push, and all of them resolve.

### What the upload declares

The project page is rendered from the newest release's metadata, so what the wheel carries is what
readers see. The evidence is the wheel built in [Before the tag](#before-the-tag), and
`tests/test_release_artefacts.py` is what holds the artefact to it.

- **`Project-URL` headers, which the artefact did not have.** `pyproject.toml` declares them now:
  `Repository` `https://github.com/xyberos/xyberos`, and `Issues`
  `https://github.com/xyberos/xyberos/issues`. Without them the Documentation, Homepage,
  Repository, and Issues links that `1.0.3` supplies are not replaced by this release — a page carries
  the newest release's metadata, so they are dropped by it.
- **`Documentation` is `https://docs.xyberos.com`.** It pointed at the repository's `docs/` directory
  while the domain served a stale build of the 1.x line; that deployment was deleted on 2026-10-12, the
  domain was attached to this line's Cloudflare Worker, and the value followed. Advertising another
  line's site from this line's page would have been worse than linking the source tree, which is why
  the value moved last rather than first ([the documentation site plan](../site/implementation.md)
  records the order).
- **Absolute links in the long description.** `readme = "README.md"` ships as
  `Description-Content-Type: text/markdown`, and a relative target in it resolves against
  `https://pypi.org/project/xyberos/` rather than the repository, so each one becomes a dead link on
  the page most readers arrive at. Thirty-five targets used to be relative — `docs/release.md`,
  `examples/hello_app/README.md`, `LICENSE`, `CHANGELOG.md` — and all of them are absolute now. The
  release-artefact test fails the build if one becomes relative again.
- **`keywords`, which were also absent.** They are an indexed search field, and the same edit fills
  them.

### The publishing workflow

Publication runs through [.github/workflows/publish.yml](../.github/workflows/publish.yml) and uses
trusted publishing: the run authenticates with GitHub's OIDC token and stores no credential, so there
is no token to rotate and none to leak. A project-scoped API token would work too and needs no
index-side configuration, but it buys nothing this pipeline needs in exchange for a long-lived secret
to protect.

The workflow is started by hand and takes one input: the version that is already tagged `v<version>`.
It checks out the tag, refuses to continue unless the request, the source, and the changelog all name
the same version, verifies the metadata with `twine check --strict`, installs the built wheel and asks
it its version, and only then uploads to PyPI — with a signed provenance attestation for each file,
which the publisher produces by default under trusted publishing. It does not repeat the test suite,
because `ci.yml` already runs it on every push to the default branch; the gate this workflow adds is
that the artefact agrees with what it claims to be.

**The publisher registered on PyPI has to match this file exactly.** A mismatch is the failure that
looks like a broken login rather than a configuration error, and the field most likely to cause one is
the last, which PyPI marks optional:

| Field | Value |
| --- | --- |
| PyPI project name | `xyberos` |
| Owner | `xyberos` |
| Repository | `xyberos` |
| Workflow | `publish.yml` |
| Environment name | **left empty** |

The environment is empty because the publish job declares none: a job that declares one puts an
`environment` claim into the OIDC token, and PyPI then has to find that claim in its record. The trade
is deliberate — an environment is also where a required reviewer would live, so the only thing between
this workflow and a release is the person who starts it, which is the same gate the rest of this guide
describes in words instead of in configuration.

The job that publishes holds `id-token: write` and the job that builds holds `contents: read`, so a
compromised build step cannot mint an upload identity for itself.

### The first upload

1. **Publish.** Start `Publish` with `version` set to the version being released. This is the upload,
   and the only one this line makes, so the run is the last chance to stop: the checks inside it are the
   subject of the section above, and everything before it in this guide happens on a checkout. The build
   job uploads the sdist and the wheel together, so no index state can resolve a version for which only
   half an artefact exists.
2. **Check resolution, not just installation.** From an empty environment:

   ```powershell
   python -m pip index versions xyberos
   python -m pip install xyberos
   ```

   `2.0.0` must be the newest version listed and the install must land on it rather than on `1.0.3`.
   An unconstrained install is the only check that distinguishes "published" from "reachable", and it
   is the check a name collision breaks silently.
3. **Re-run the clean-install smoke test against the index** rather than against a local wheel, with
   the same expectation: `xyberos --version` reports `2.0.0`, and installing the extras resolves the
   optional dependencies from the published metadata.
4. **Record the resolution check in the release notes** as the evidence that the collision resolved
   the intended way, and attach the SBOM alongside the artefacts.

There is no rehearsal index in that path. A rehearsal could only show the mechanics, since the one
question that matters — whether `2.0.0` outranks the published line — is a question about PyPI and can
be asked nowhere else. What stands in for it is the run's own preface: the tag is the only source, the
version is checked against the source and the changelog before anything is built, the metadata is
checked with `twine check --strict`, and the built wheel is installed and asked its version. If
something is still wrong, the release is withdrawn rather than corrected in place — see
[Rollback and withdrawal](#rollback-and-withdrawal).

## Releasing beside the published 1.x line

`xyberos` is already published at `1.0.3` by this project, and it is a different codebase
([ADR 0017](./adr/0017-release-identity-and-lineage.md)). Publishing `2.0.0` changes nothing about it:
the old release is neither edited nor yanked, and an environment that pins it keeps working.

- **What a 1.x user sees.** Their next unconstrained upgrade moves them to a rewrite. The changelog
  entry says so in its first line, and the README says it where they arrive.
- **Every name beside this line is tracked in one file.** [`packages.toml`](../packages.toml) records each
  name, its import root, the core range it declares, and its status — `placeholder`, `planned`, `written`,
  `published`, or `retired`;
  `tests/test_packages_manifest.py` keeps this page, the plugin guide's catalogue, and the feature matrix
  in step with it. What follows is read from that file rather than from a blanket instruction.
- **The repin has already shipped, per name.** The three satellites [ADR 0017](./adr/0017-release-identity-and-lineage.md)
  names — `xyberos-auth` `0.1.2`, `xyberos-db` `0.1.2`, and `xyberos-mcp` `0.2.2` — declare
  `xyberos>=1.0,<2`, so an unpinned install of any of them still resolves the 1.x core. There is no
  blanket repin left to do: a name is repinned when it is touched, and the manifest records what each one
  declares. Without that pin, `pip install xyberos-auth` resolves the core to `2.0.0`, whose
  `xyberos.runtime` and `xyberos.plugins` are unrelated to what those packages were written against, and
  the install breaks with no version conflict to warn anyone — a resolver is not a reader.
- **A retired name gets a pointer, and nothing else.** `xyberos-db` `0.1.2` points at `xyberos[database]`
  and the provider seam, in a metadata-only `0.1.3` whose description names the replacement and which keeps
  the `xyberos>=1.0,<2` pin, published in the same window as the upload. `xyberos-metrics`, whose capability
  ships as `xyberos.http.RequestMetricsMiddleware`, has nothing to point *from*: no release under that name
  resolves on the index, so this line publishes no patch for it, and a `0.2.x` upload would create the name
  rather than retire it — the second answer to one question the pointer rule exists to avoid. No shim ships,
  and no 2.x release is cut under either name.
- **What to tell them.** A project that depends on the 1.x API should pin `xyberos<2`; a project that
  wants this line installs `xyberos>=2` into a clean environment rather than upgrading in place.
- **What could soften the upgrade instead of only documenting it.** A final patch on the 1.x line — a
  new upload rather than an edit to a published release — that warns on import and points at this line
  would reach users who never read a changelog. It is optional, it belongs to the other repository,
  and it works against the frozen state ADR 0017 records for that line.
- **What cannot be fixed.** The two lines install the same import root (`xyberos`) and define
  `xyberos.runtime` and `xyberos.plugins` differently, so one environment holds one or the other. No
  packaging trick changes that; a project that needs both runs two environments.
- **What the index does with the name.** The project page, its description, and its classifiers become
  this line's. That is intended: one name, one current line, with the previous one still installable.
  The Documentation link is the exception, and it is the one part of the page this release does not
  improve — see precondition 4 above.

## Rollback and withdrawal

A release is withdrawn, never edited: an artefact that has been installed anywhere cannot be corrected
in place.

- **Nothing is broken, but the release should not be the default.** Mark it as a pre-release or yank
  it on the index so new installs do not select it, and leave it downloadable so existing pins keep
  working. Then publish a patch release with the fix.
- **A release is broken in a way that makes it unsafe to run.** Yank it, publish a patch release with
  the fix, and say so in the changelog under "Security" or "Fixed" — with the impact and the affected
  versions, not just the change.
- **A release is broken in a way that cannot be fixed forward quickly.** The rollback instruction to
  users is to pin the previous version, and the changelog entry states that pin explicitly. Every
  release keeps the previous artefact available for exactly this case; that is a reason not to delete
  old releases.
- **A durable journal was written by a newer build.** Rolling the *package* back is not enough if the
  journal schema moved: the journal refuses a file newer than the package, on purpose, rather than
  opening it at the older worker's risk. In that case the rollback is a restore from the backup taken
  before the upgrade — see the journal's [backup and restore](./durable.md#backup-and-restore)
  section.

## What is deliberately not automated

- **No publish-on-tag job.** Publishing is a decision, and the evidence for it is a person confirming
  the gate rows rather than a green build.
- **No automatic version bump from commit messages.** The version number is a promise about
  compatibility, and this project's rules for it are not derivable from a commit prefix.
- **No separate attestation step.** `pypa/gh-action-pypi-publish` signs an attestation for every file it
  uploads, using the same OIDC identity it authenticates with, so provenance comes from the publish run
  rather than from a job this repository has to maintain. What it does not replace is the human gate: an
  attestation says where an artefact came from, not that anyone checked the release rows.
