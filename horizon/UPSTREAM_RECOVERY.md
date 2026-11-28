# Horizon upstream recovery and independence

Stage 3.1 for PR #8 preserves the existing Minecraft 26.3 build inputs. The
SDK job at `f33b426` failed during Git authentication to the upstream, before
it ran the compiler. The mirror is a transport for one pinned commit. Its
default branch is outside the build. [Failed SDK run](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/46152726409)

| Project | Commit | Git tree | Root license at the pin |
| --- | --- | --- | --- |
| Horizon | `c78187dffffb60f31517eadcb87413386e8ce729` | `16cfda3ed3b1674d3f51c2fdc6c9a93237b7d275` | MIT, Ludovic Marie and Horizon contributors |
| Horizon Mixins | `5a64af938ec86b00d53d16a408aabc0038fb3e57` | `1aa65935448bae72719c7a02b503a4216593fbd1` | MIT, levzzz |

## Provenance and redistribution

An exact Git fetch from `rdbtCVS/horizon` matched the saved upstream commit,
tree, full source archive, `Cargo.lock` and `LICENSE`. The mirror's current
default-branch metadata shows LGPL-3.0. Its license file at the selected
commit is MIT and matches the prior local clone byte for byte.
[Mirror commit](https://github.com/rdbtCVS/horizon/commit/c78187dffffb60f31517eadcb87413386e8ce729)

The root MIT notices cover the two pinned projects. Horizon also contains
separately licensed vendored Rust and C code, fonts, icons and other assets.
Retain the pinned `THIRD_PARTY_NOTICES.md`, individual license files and
copyright headers. Audit the exact redistribution set and its dependency
notices before publishing any source bundle. A current-tree license check
does not clear material found only in historic commits. The recovery Git
bundles, local dependency cache, worlds and game resources are private.
The PR contains verification code, pins and documentation. The existing
native-tools CI artifact now carries the pinned license and notice files.

## Restore and build

The source lock records the commit, tree and SHA-256 of each lockfile and root
license. The checkout helper verifies them before creating the output checkout.
The CI jobs still compile from source and run their original validations. Rust
1.99.1 matches the local Horizon build. Mixins uses its own pinned Rust 1.95.0.

```sh
python3 horizon/tools/checkout_horizon_source.py horizon /path/to/horizon
python3 horizon/tools/checkout_horizon_source.py horizon /path/to/offline-horizon \
  --bundle /path/to/recovery/horizon-pinned.bundle
python3 horizon/tools/checkout_horizon_source.py mixins /path/to/offline-mixins \
  --bundle /path/to/recovery/horizon-mixins.bundle
```

In the retained cloud workspace, recovery inputs are under
`/workspace/horizon-stage31-recovery`. The registry snapshot archives cached
crate archives and their index with the original lockfiles. Restore it under
a private `CARGO_HOME` and use the recorded toolchains and system-package
inventory. Additional OS or target dependencies may be required on another
host. Verify archive hashes against `SHA256SUMS` before restoring.

```sh
cargo +1.99.1 build --manifest-path /path/to/offline-horizon/Cargo.toml \
  --profile fast --locked --offline -p cargo-horizon-mod --bin cargo-horizon-mod
cargo +1.95.0 build --manifest-path /path/to/offline-mixins/Cargo.toml \
  --release --locked --offline
```

For the TechQuest engine, apply the four sealed 11b Mixins manifests and the
reviewed world-pack corrections to a fresh copy of the pinned Horizon source.
Mixins rejects symlinks, so materialize the tree's `CLAUDE.md -> AGENTS.md`
documentation link in that staging copy and record the verified revision in
`.horizon-revision` when using a Git archive. For Mixins inputs, use the
source payloads from the four checksum-verified 11b native bundles. The
private recovery directory contains the exact local rebuild commands.

```sh
cargo +1.99.1 build --manifest-path /path/to/generated-horizon/Cargo.toml \
  --profile fast --locked --offline --no-default-features \
  --features ureq/native-certs,ureq/proxy-from-env \
  -p horizon-client --bin horizon-client
```

## Local checks and remaining recovery scope

The recovered Horizon build tree and Mixins compile offline. Native runtime
verification uses isolated worlds and already prepared game resources.
The draft Small Tank diff and untracked files are preserved separately and
remain in the working tree. Existing profile locks and EULA settings remain
in their local profile directories.

The available mirror can recover the entire history reachable from the Horizon
build pin. Other local Horizon refs came from a partial clone. Their ref map
and locally available packs are preserved separately. Any missing objects
outside the pinned history still need an accessible historical source.
The public CI checkout uses the mirror. The private archives provide a
network-independent input to the same checkout helper.
