# Contributing Guide

Contributing to Xyberos takes one of two paths:

| Path | What you contribute | Guide |
| ---- | ------------------- | ----- |
| **Core** | Bug fixes, tests, docs, features, RFCs — changes *inside* `xyberos/` | This page |
| **Plugins** | New capabilities (LLM providers, tools, memory, knowledge, integrations) — **external**, no core changes | [Build & Contribute Plugins](plugin-contribution.md) |

> **Building a plugin?** That's the fastest path — the toolkit does most of the
> work: `xyberos plugin create` → implement → `xyberos plugin validate` →
> `xyberos plugin repair`. See [Build & Contribute Plugins](plugin-contribution.md)
> and the [Learn 24 — Build & Contribute Plugins](learn/24-plugin-development.md)
> walkthrough for the
> `CREATE → IMPLEMENT → TEST → VALIDATE → DOCUMENT → PACKAGE → PR` pipeline.

This page is the **core** contribution guide. It mirrors the repository's root
[`CONTRIBUTING.md`](https://github.com/xyberos/xyberos/blob/master/CONTRIBUTING.md).

--8<-- "CONTRIBUTING.md"
