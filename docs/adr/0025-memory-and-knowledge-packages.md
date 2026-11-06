# ADR 0025: Memory and knowledge as separate ecosystem packages

**Status:** accepted

## Context

Xyberos already has the extension points these capabilities need: `DatabaseProvider` for application
data and `EmbeddingModel` for provider-neutral embeddings. Their lifecycle and policy should not
become implicit core behavior. At the same time, applications need a supported way to keep
conversation history and scoped facts, and to retrieve cited passages from an application-owned
knowledge source.

The existing vector and document packages target the 1.x API and cannot be installed against this
line. Reusing them would couple the add-ons to incompatible contracts rather than to this line's
public API.

## Decision

**Ship `xyberos-memory` and `xyberos-knowledge` as separate standalone distributions in
`xyberos/xyberos-plugins`.** Each owns a top-level import root, typed public API, tests, README, and
its own release cadence, following ADR 0018's package placement.

- **`xyberos-memory` owns persistent conversation history and explicitly scoped facts.** It uses the
  application's `DatabaseProvider`; the application chooses and owns the database provider and its
  lifecycle. A scope is an application-supplied namespace and key, not an authorization identity.
  Callers remain responsible for authenticating and authorizing access to each scope.
- **`xyberos-knowledge` owns document chunking, embedding, retrieval, and citation results.** It
  consumes the core `EmbeddingModel` protocol and defines a `VectorStore` protocol. The application
  supplies a vector-store implementation; this package ships no vendor backend.
- **Knowledge does not own prompt assembly, chat generation, agent loops, ingestion transports, or
  authorization.** Applications compose returned passages and citations according to their own
  policy.
- Neither package registers itself implicitly as a plugin or modifies application configuration.
  Applications construct the service explicitly and pass its dependencies.

This supersedes only ADR 0018's refusal of RAG and its vector-store/indexing capabilities. Other
refusals and the four placement constraints remain unchanged.

## Consequences

- The core remains free of database, vector-store, and retrieval dependencies; `pip install xyberos`
  does not change.
- A vector-store adapter can be released independently and is tested against
  `xyberos_knowledge.testing.assert_vector_store_contract`.
- A useful knowledge installation requires both an embedding provider and a vector store. The
  package does not disguise either missing dependency with a no-op implementation.
- These packages are initially recorded as `written` in `packages.toml`; that status does not claim
  a PyPI release exists.
- Scopes are data partitioning inputs, not an authorization boundary. A caller that accepts a
  user-controlled scope without authorization can disclose another scope's data.
