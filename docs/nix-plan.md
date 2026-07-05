# Nix Migration Plan

## Purpose

This document records the Nix migration work for making the UI runnable
without Docker and tracks the remaining follow-up items.

Target outcomes:

- `nix develop` provides a usable local development environment.
- `nix run .` starts the packaged UI without Docker.
- Documentation matches the actual supported workflows.

## Verified Current State

The following items are verified against the current codebase.

- `flake.nix` and `flake.lock` exist and standard flake commands now work from the repository root.
- Runtime path handling is no longer Docker-only. The backend resolves `MRTKLIB_WORKSPACE_DIR`, `MRTKLIB_DATA_DIR`, `MRTKLIB_SYSTEM_DIR`, `MRTKLIB_CORRECTIONS_DIR`, `MRTKLIB_MRTK_BIN`, `MRTKLIB_STATIC_DIR`, `MRTKLIB_NETRC_PATH`, and `MRTKLIB_CREDENTIALS_FILE` while preserving Docker's logical `/workspace`, `/data`, and `/opt/mrtklib` paths in saved configuration.
- `nix flake show .` succeeds in the current worktree.
- `nix flake check` succeeds on `x86_64-linux` in the current worktree.
- `nix develop` now provides Python 3.12, `uv`, `ruff`, Node.js, CMake, Git, LP64 OpenBLAS, and `mrtk`; it also exports `MRTKLIB_WORKSPACE_DIR`, `MRTKLIB_DATA_DIR`, `MRTKLIB_SYSTEM_DIR`, `MRTKLIB_MRTK_BIN`, `MRTKLIB_CORRECTIONS_DIR`, `MRTKLIB_CREDENTIALS_FILE`, and `MRTKLIB_NETRC_PATH`.
- `nix build .#frontend`, `nix build .#backend`, `nix build .#mrtklib`, and `nix build .#default` succeed in the current worktree.
- The default MRTKLIB input is the portable GitHub `v0.7.6` archive. A local editable checkout can be supplied explicitly with `--override-input mrtklib-src path:/path/to/MRTKLIB` without changing `flake.lock`.
- The MRTKLIB package contains the configuration, bundled receiver presets, CLAS presets, and correction files used by the Docker image.
- `nix run .` starts the packaged app in the current worktree, `GET /api/health` returns `200`, and the root URL serves the built SPA.
- A harmless MRTKLIB CLI smoke test succeeds via `nix develop --command mrtk --help`.
- `path:$PWD` is no longer required for the standard workflow.
- Observation QC still needs an explicit packaging decision because the feature depends on `cssrlib` at runtime while the default backend package remains buildable without it.
- The README and `frontend/README.md` have been updated to describe the current Nix workflow, but remaining scope notes still belong here.

## Scope Decision

Before implementation, decide the supported Nix surface explicitly.

Required decision:

1. Support only Linux, or also support Darwin.

Current flake outputs only define:

- `x86_64-linux`
- `aarch64-linux`

If Darwin support is required, add it as a separate task. If not, document Nix support as Linux-only.

## Work Plan

Current status in this worktree:

- Phase 1 is complete on `x86_64-linux`.
- Phase 2 is complete on `x86_64-linux`.
- Phase 3 is complete for the current default backend package, with Observation QC and `cssrlib` still requiring an explicit packaging decision.
- Phase 4 is complete on `x86_64-linux`.
- Phase 5 is complete on `x86_64-linux`.
- Phase 6 is partially complete.
- Phase 7 is partially complete.

### Phase 1: Make the flake consumable

Status: complete in the current worktree on `x86_64-linux`.

Tasks:

1. Add `flake.nix` to Git.
2. Generate and commit `flake.lock`.
3. Verify that standard commands work from the repository root:
   - `nix flake show`
   - `nix develop`
   - `nix build`
4. Stop treating `path:$PWD` as a supported workflow. Keep it, if at all, only as a temporary local debugging workaround while the flake files are not yet tracked.

Reason:

- Without Git-tracked flake files, the normal `nix .` workflow is not usable.
- `path:$PWD` changes the source semantics from Git source to local path source and can mask reproducibility problems.

Acceptance criteria:

- `nix flake show` succeeds from the repo root without `path:$PWD` workarounds.
- The documented workflow no longer relies on `path:$PWD`.

### Phase 2: Make the frontend package buildable

Status: complete in the current worktree on `x86_64-linux`.

Tasks:

1. Build the frontend derivation once to obtain the real NPM dependency hash.
2. Replace `lib.fakeHash` with the actual `npmDepsHash`.
3. Re-run `nix build .#frontend`.
4. Confirm the build output contains the expected static assets.

Reason:

- `buildNpmPackage` cannot be part of a reproducible flake while `npmDepsHash` is still a placeholder.

Acceptance criteria:

- `nix build .#frontend` succeeds reproducibly.
- The output contains `share/mrtklib-web-ui/static/index.html` and bundled assets.

### Phase 3: Make the backend package buildable

Status: complete for the current default backend package in the current worktree on `x86_64-linux`.

Tasks:

1. Replace string literals in `backendDeps` with actual Nix Python package references.
2. Verify availability of all required Python packages in the selected `nixpkgs` revision.
3. Decide whether Observation QC remains part of the default backend package. `cssrlib` is functionally required for that feature at runtime, so feature scope and packaging must match.
4. If Observation QC remains in the default backend, ensure `cssrlib` is included in the default backend package or explicitly disable the feature under Nix until it is available.
5. Re-run `nix build .#backend`.

Minimum package set that must resolve cleanly:

- `fastapi`
- `httpx`
- `numpy`
- `pydantic`
- `uvicorn`
- `websockets`
- `watchfiles`
- `python-multipart`
- `python-socketio`

Reason:

- The backend derivation currently fails before packaging because some dependencies are not defined as build inputs.

Acceptance criteria:

- `nix build .#backend` succeeds.
- The package passes `pythonImportsCheck = [ "mrtklib_web_ui.main" ]`.
- If Observation QC is part of the default backend package, add a runtime smoke check that proves `cssrlib` is actually importable for that feature path.

### Phase 4: Make `mrtk` available in the Nix development workflow

Status: complete in the current worktree on `x86_64-linux`.

Tasks:

1. Decide whether `nix develop` should include the packaged `mrtklib` binary.
2. If yes, add the `mrtklib` derivation to the dev shell environment.
3. Export `MRTKLIB_MRTK_BIN` from the dev shell if `mrtk` is part of the supported development workflow.
4. Decide whether `MRTKLIB_CORRECTIONS_DIR` is required in the dev shell or only in the packaged runtime. If it is required for the supported workflow, export it and document why.
5. Verify that `command -v mrtk` succeeds inside `nix develop`.

Reason:

- The backend can resolve `mrtk` from environment or `PATH`, but the current dev shell does not actually provide it.
- Without `mrtk`, the UI shell is only partially functional.

Acceptance criteria:

- Inside `nix develop`, `command -v mrtk` succeeds.
- A harmless MRTKLIB CLI smoke test supported by the pinned MRTKLIB revision succeeds.
- The API endpoint for MRTKLIB version may be used as a secondary check, but not as the sole proof of correctness because it currently only checks path existence.

### Phase 5: Make the packaged app runnable

Status: complete in the current worktree on `x86_64-linux`.

Tasks:

1. Rebuild:
   - `nix build .#mrtklib`
   - `nix build .#frontend`
   - `nix build .#backend`
   - `nix build .#default`
2. Run the packaged app with `nix run .`.
3. Verify that the app starts with:
   - writable workspace directory
   - readable data directory
   - packaged frontend static files
   - packaged `mrtk` binary
4. Confirm that the browser UI loads from the backend-served static bundle.
5. Verify actual `mrtk` execution in the packaged runtime with a harmless smoke test. Do not treat path-existence checks alone as sufficient.

Reason:

- The project goal is not just to define derivations, but to make the assembled UI runnable without Docker.

Acceptance criteria:

- `nix run .` starts the server successfully.
- `GET /api/health` returns `200`.
- Opening the root URL serves the built SPA rather than a missing static-file response.
- The packaged runtime can execute a harmless MRTKLIB CLI smoke test successfully.
- If `GET /api/mrtklib/version` is used, treat it only as a secondary signal because it currently reports path existence rather than process execution.

### Phase 6: Decide the supported development workflow

Status: partially complete. `nix develop` works, but the exact supported editable-development command set still needs to be finalized and documented as policy rather than as observed behavior.

Tasks:

1. Decide whether the official Nix development path is:
   - packaged app only via `nix run`
   - or editable development via `nix develop` plus `uv` and `npm`
   - or both
2. If editable development is supported, verify:
   - `nix develop -c uv sync`
   - `nix develop -c npm --prefix frontend ci`
   - backend dev server start
   - frontend dev server start
   - Vite proxy to backend
3. Document the exact commands.

Reason:

- `nix run` and `nix develop` solve different use cases. The repository should define both explicitly rather than leaving them implicit.

Acceptance criteria:

- The supported development workflow is written down and reproducible from a clean checkout.

### Phase 7: Update documentation

Status: partially complete. The main README files now describe the current Docker and Nix workflows, but remaining scope and support-policy decisions still need to be reflected consistently.

Tasks:

1. Update `README.md` to reflect the supported workflows.
2. Keep Docker documentation if Docker remains supported.
3. Add a Nix quick start section.
4. Explain the logical `/workspace` and `/data` paths versus their actual host directories under Nix.
5. Document how to override:
   - `MRTKLIB_WORKSPACE_DIR`
   - `MRTKLIB_DATA_DIR`
   - `MRTKLIB_SYSTEM_DIR`
   - `MRTKLIB_CORRECTIONS_DIR`
   - `MRTKLIB_MRTK_BIN`
   - `MRTKLIB_STATIC_DIR`
   - `MRTKLIB_NETRC_PATH`
   - `MRTKLIB_CREDENTIALS_FILE`
6. Align version claims in `README.md` with the current project metadata such as Python, React, and Mantine versions.
7. Replace or trim stale Docker-only statements where they are no longer accurate.
8. Replace the template `frontend/README.md` if it is no longer useful.

Reason:

- Current documentation describes Docker as the only supported runtime, which no longer matches the implementation direction.

Acceptance criteria:

- A new user can choose Docker or Nix based on the README alone.
- The README does not claim Docker-only operation if Nix is supported.

## Validation Checklist

The following checks should all pass before calling the Nix workflow complete.

```bash
nix flake show
nix flake check
nix build .#mrtklib
nix build .#frontend
nix build .#backend
nix build .#default
nix develop -c zsh -lc 'command -v mrtk'
nix run . &
curl -fsS http://127.0.0.1:8000/api/health
```

In addition, run one harmless MRTKLIB CLI smoke test that is supported by the pinned MRTKLIB revision. Do not rely only on `GET /api/mrtklib/version`, because the current endpoint reports path existence rather than verified process execution.

If editable development is an official workflow, also verify:

```bash
nix develop -c uv sync
nix develop -c npm --prefix frontend ci
nix develop -c uv run uvicorn mrtklib_web_ui.main:app --host 127.0.0.1 --port 8000
nix develop -c npm --prefix frontend run dev
```

## Open Issues and Decisions

These items still require an explicit decision during implementation.

- Whether Nix support is Linux-only or cross-platform.
- Whether Observation QC remains part of the default backend package. If yes, `cssrlib` must be available or the feature must be disabled clearly under Nix.
- Whether `nix develop` must be fully functional for MRTKLIB execution, or only provide general build tools.
- Whether Docker remains the primary workflow or becomes an alternative workflow.

## Definition of Done

Nix support is complete only when all of the following are true.

- `nix flake show` works from a clean checkout.
- `nix develop` provides a documented and functional development environment.
- `nix run .` starts the UI without Docker.
- `mrtk` is available wherever the supported workflow requires it.
- The README describes the actual supported workflows accurately.
