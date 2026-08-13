# Comparable Architecture Review

> **Lifecycle: COLD historical research.** This document explains a completed Seedance investigation and has no authority to create workflows, call external APIs, spend quota, or define the current provider-release architecture. Read `docs/PROJECT_STATE.json` for current work and `strategy/executable-model-graph-v0.2.json` for bounded model evidence.

Purpose: prevent closed-door invention. This review compares mature systems only on structural questions relevant to this project: tool invocation, asset/resource transport, long-running tasks, credentials, failure recovery, and what should or should not be copied.

## 1. Model Context Protocol (MCP)

Official references:

- https://modelcontextprotocol.io/specification/2025-11-25
- https://modelcontextprotocol.io/specification/2025-11-25/server/resources
- https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks

### Structural observations

MCP separates several concepts that our early experiments repeatedly conflated:

- `Tools`: model-invokable operations with explicit input/output schemas.
- `Resources`: URI-addressed contextual/data objects such as files.
- `Tasks`: durable execution state for expensive/deferred operations, with task IDs, status polling, result retrieval, cancellation and TTL.
- Capability negotiation: a client should not assume a server supports an operation until the relevant capability is declared.
- Tool results may contain text, image/audio content, structured content, embedded resources, or resource links.

### Conceptual reuse

Adopt the separation, even if GitHub remains the current physical transport:

```text
Control plane: generate_video(...)
Resource plane: reference image / output MP4
Task plane: task id / status / result
Authorization plane: user grant + secret scope
```

Do not encode these four concepts as one undifferentiated workflow string.

### Do not over-copy

MCP Tasks are an evolving protocol feature and are not required for our already working GitHub/Ark route. The useful lesson is the state-machine abstraction, not an immediate requirement to rebuild the project as an MCP server.

## 2. Pipedream MCP

Official references:

- https://pipedream.com/docs/connect/mcp
- https://pipedream.com/docs/connect/mcp/developers

### Structural observations

Pipedream exposes a large catalog of API operations as standardized agent tools and keeps authentication/credential handling outside the model. Its managed MCP layer emphasizes:

- consistent tool interfaces over many APIs;
- managed OAuth/credential storage;
- tool discovery/exposure;
- credentials not being directly exposed to the model.

### Conceptual reuse

- Treat provider credentials as execution-environment state, not prompt/context data.
- Normalize heterogeneous provider APIs behind a small capability vocabulary.
- A model should select an operation by semantics; provider-specific HTTP details belong in an adapter.

### Do not over-copy

Pipedream solves broad SaaS integration and authentication. Our immediate use case already has a working authenticated execution path through GitHub Actions. Adding another hosted integration layer is not justified unless it removes a demonstrated limitation rather than a hypothetical one.

## 3. n8n

Official references:

- https://docs.n8n.io/
- https://docs.n8n.io/workflows/executions/all-executions/
- https://docs.n8n.io/hosting/scaling/external-storage/

### Structural observations

n8n treats workflow execution history and retry as first-class operational concerns. Failed executions can be retried using previous execution data. It also explicitly treats binary data as a separate storage concern; external S3 storage exists for binary execution data in supported enterprise configurations.

### Conceptual reuse

- Persist enough task metadata to diagnose/retry a failed generation without reconstructing the experiment from chat memory.
- Separate binary asset lifecycle from JSON/control metadata.
- Record execution status transitions and exact failure location.

### Do not over-copy

Using n8n only to reproduce our already-working GitHub Actions + Artifact path would add another runtime and another credential boundary. Also, its documented external binary storage feature is not a free-community primitive, so it should not be assumed to remove our constraints for free.

## 4. GitHub Actions (historical physical implementation)

Official references:

- https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts
- https://docs.github.com/en/actions/concepts/security/secrets
- https://docs.github.com/en/rest/actions/artifacts

### Structural observations

At investigation time, GitHub supplied three useful physical primitives for that Seedance study:

- Actions: remote execution of code and network calls.
- Secrets: credential injection into selected workflows without placing the secret in repository source.
- Artifacts: binary files produced by workflow runs can persist after the job and be downloaded via API.

Our own E2E tests additionally established that the connected GitHub tool can:

- write chat-uploaded binary data into the repository via Git blobs;
- expose that input through a public repository URL;
- execute Ark/Seedance text-to-video and image-to-video jobs;
- return the generated MP4 through an Artifact into the current ChatGPT conversation.

### What GitHub is and is not

In that completed investigation, GitHub was a successful **physical transport/execution backend**. That historical fact does not make it the semantic model of the current provider project.

Use conceptual layers above it:

```text
User intent
   ↓
Capability request
   ↓
Resource references + task state
   ↓
GitHub/Ark adapters
```

This permits later replacement of GitHub without rewriting the capability semantics.

## 5. Cross-system conclusions

### Reusable invariants

1. Tool/capability semantics should be independent of provider HTTP details.
2. Binary resources should have explicit identities/references; they should not be treated as incidental strings.
3. Long jobs require explicit task state, result retrieval and failure attribution.
4. Secrets/credentials belong outside model-visible prompts and source-controlled request data.
5. Failure recovery requires execution metadata, not merely a final success/failure boolean.
6. Capability negotiation/evidence should precede using an edge as executable infrastructure.

### Historical architectural decision

Do **not** introduce MCP, Pipedream, n8n, R2, or a new Asset Gateway merely to make the already-proven single-video path look more conventional.

At that time, the project chose to:

- keep GitHub Actions + GitHub binary/blob transport + Artifacts as the physical backend for the completed probes;
- adopt MCP-like conceptual separation of Tool / Resource / Task / Authorization;
- add explicit task/evidence metadata and narrow adapters;
- introduce a new subsystem only after a concrete requirement is shown to be impossible or materially inefficient through the existing verified backend.

That decision was conditional, not permanent, and its one-off executable workflows have since been retired. Its historical invalidators included demonstrated scaling, privacy, file-size, latency, concurrency, retention, or capability requirements that the backend could not satisfy within the intended use case.
