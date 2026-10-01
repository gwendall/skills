---
name: eas-monorepo-release
description: Runbook for building and shipping an Expo app from a large monorepo to TestFlight/App Store with EAS. Use when `eas build`/`eas submit` fails (archive > 2 GB, XCODE_BUILD_ERROR AnyMap/nitro, alpha-channel icon), or when a TestFlight build doesn't show up for a tester. Covers the oversized-archive workaround, native version pins, and TestFlight management via the App Store Connect API. Triggers on "eas build fails", "archive too big", "AnyMap getBigInt", "App Store icon rejected", "nothing in TestFlight", "TestFlight invitation revoked", "ship to TestFlight".
compatibility: Requires eas-cli, git, python3 + a venv (pyjwt cryptography requests) for the App Store Connect client. The ASC API key (Admin, account-level) is expected under ~/.config/appstoreconnect/ (config.json + .p8). macOS (sips/PIL for the icon fix).
homepage: local
metadata: {"version":"1.2.0","openclaw":{"requires":{"bins":["eas","git","python3"]},"emoji":"rocket"}}
---

# EAS monorepo → TestFlight (runbook)

Real blockers hit shipping Expo apps from a large pnpm monorepo, with validated fixes. A big monorepo has specific traps that a standalone app never hits. Order below: the 3 build blockers, then the TestFlight flow.

## Credential prerequisites
- **iOS signing**: `eas credentials -p ios` (interactive, Apple 2FA) - generates the distribution certificate + provisioning profiles. Once per app.
- **App Store Connect API key** (Admin, account-level, reusable across all projects): stored under `~/.config/appstoreconnect/` (`.p8` + `config.json` with Issuer ID + Key ID). Used to submit without 2FA AND to drive TestFlight via the API.

## Blocker 1 - `Project archive is X GB. Maximum allowed size is 2.0 GB`
**Cause**: EAS uploads the working tree **plus `.git`**. In a large monorepo the `.git` can be > 1 GB (large binaries - demo videos, model files, audio - committed in history/HEAD across sibling apps). `.git` **cannot be excluded via `.easignore`** (EAS bundles it). `node_modules` IS excluded, so it's rarely the culprit.

**Diag**: `du -sh .git` at the repo root. If it's > ~1 GB, that's your archive bloat.

**Fix (non-destructive)**: build from a **clean context** = `git archive HEAD` (drops `.git` + media via `.gitattributes export-ignore`), fresh `git init` (tiny `.git`), `pnpm install` (creates node_modules - required for the expo-dev-client check, excluded from the upload via `.gitignore`), then `eas build` from there. In practice this dropped a 3+ GB archive to ~500 MB.
→ Ready-made, generic script (included with this skill): run `bash scripts/eas-build-clean.sh [development|preview|production]` from the app dir that holds `eas.json`. It auto-detects the repo root and the app's path within it - no per-app editing needed.

**Durable fix (team decision, destructive)**: strip the large media out of git (`git-filter-repo`/BFG + Git LFS) → `.git` ~100 MB → build from the normal repo, no script. Rewrites history (force-push, team re-clone).

## Blocker 2 - `XCODE_BUILD_ERROR`: `AnyMap has no member 'getBigInt'/'isBigInt'`
**Cause**: native crypto version conflict. `react-native-quick-crypto` is generated with a `nitrogen` of version N; its C++ calls `AnyMap` methods (`getBigInt`) that were **renamed** (`isInt64`) in newer `react-native-nitro-modules`. If the app pins an incompatible nitro → build breaks.

**Diag**: `cat node_modules/.pnpm/react-native-quick-crypto@*/node_modules/react-native-quick-crypto/package.json` → look at `devDependencies.react-native-nitro-modules` (= generation version, e.g. 0.33.2). Check the installed nitro's `AnyMap.hpp` actually has `getBigInt`.

**Fix**: pin `react-native-nitro-modules` to the version quick-crypto expects (e.g. `0.33.2`) in the app + a **global pnpm override** (root `pnpm.overrides`). Verify nothing else requires a newer nitro (`@kingstinct/react-native-healthkit` tolerates `>=0.30`).

## Blocker 3 - App Store submission fails: `Something went wrong when submitting`
**Opaque** error (error/logsUrl null via the EAS API). **Top cause: icon with an ALPHA CHANNEL**. The App Store rejects any `icon.png` with an alpha channel, **even a fully-opaque one**.

**Diag**: `sips -g hasAlpha assets/*/icon.png` → `hasAlpha: yes` = culprit.
**Fix**: convert RGBA→RGB (strips the channel). If the alpha is fully opaque (`PIL: alpha min==255`), **no visual change**:
```python
from PIL import Image
Image.open("assets/production/icon.png").convert("RGB").save("assets/production/icon.png")
```
Then **rebuild** (the icon is baked into the binary) + resubmit.

## Full TestFlight flow
1. `bash scripts/eas-build-clean.sh production` (store-distribution build, works around the archive).
2. `eas submit -p ios --latest --non-interactive` - needs `ascAppId` in `eas.json` (`submit.production.ios.ascAppId`) + the ASC API key. The first interactive submit creates the app record + the key.
3. **An uploaded build does NOT appear for the tester on its own.** You need: build assigned to an internal group + tester in the group + **invitation accepted**.

### Driving TestFlight via the App Store Connect API
Generic client: `scripts/asc-api.py`. Set it up once: `python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt`. It reads the key from `~/.config/appstoreconnect/`. Useful commands:
- Diag: builds (`processingState=VALID`?, `buildBetaDetail.internalBuildState=IN_BETA_TESTING`?), groups (`isInternalGroup`), testers (`state=INVITED` vs `ACCEPTED`/`INSTALLED`).
- Create a clean internal group (`POST /v1/betaGroups`, `isInternalGroup:true`) if the auto-created "Team (Expo)" one is flaky.
- Add build + tester: `POST /v1/betaGroups/{id}/relationships/builds` and `.../betaTesters`.
- (Re)send an invitation: `POST /v1/betaTesterInvitations` (betaTester + app).

### TestFlight gotchas (from experience)
- **Apple's API returns intermittent 500s/timeouts** on the betaGroups endpoints → **retry with backoff**; it's not your config.
- **Nothing shows even though everything is configured** → the tester is `state=INVITED` (not accepted): they must **open the TestFlight email → "View in TestFlight" → accept**. A "revoked" invitation = send a fresh one.
- **Apple ID**: the TestFlight app on the iPhone must be signed in with the **same Apple ID** as the App Store Connect account, or the internal build never appears.
- Internal testers must be **App Store Connect Users** (team members).

## After setup
Later builds = `bash scripts/eas-build-clean.sh production` + `eas submit -p ios --latest --non-interactive`, then (if needed) add the build to the internal group via the API. JS-only OTA without rebuild: `eas update --branch <channel>`.
