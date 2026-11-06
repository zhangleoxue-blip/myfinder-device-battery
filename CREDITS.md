# Credits, Copyright and License Notice

## About this build

- **Maintainer / modified by:** LeoZhang
- **Copyright:** Copyright (C) 2026 LeoZhang
- **License:** GNU Affero General Public License, version 3 **only** (`AGPL-3.0-only`)
- **Source code:** https://github.com/zhangleoxue-blip/myfinder-device-battery

This program is **a modified derivative**, not an official build of the original
project. It is published by LeoZhang under the same license as the original.
The product name, application icon, `AppId` and package file name are kept from
the original on purpose; the release channel, signing key and in-app source link
have been changed to this repository.

## Original work

- **Project:** [wushuai0802/myfinder-device-battery](https://github.com/wushuai0802/myfinder-device-battery)
- **Copyright:** Copyright (C) 2026 wushuai0802
- **License:** AGPL-3.0-only (versions 1.3.4 and earlier were released under MIT;
  that relicensing does not apply to later versions)

The full license text is preserved unmodified in [`LICENSE`](LICENSE).
All original copyright and source-address notices are retained.

## Third-party components

- Battery-query modules under `engine/providers` are adapted from
  [HeyOkay/HaloBattery](https://github.com/HeyOkay/HaloBattery), commit
  `2251f0534a8e886c9692ead42056059b4f69d8c0` (MIT). Its copyright and permission
  notice is preserved in `engine/licenses/HaloBattery-MIT.txt`.
- The complete third-party list is preserved in
  [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and `engine/licenses/`.

## Changes made in this derivative

Recorded on **2026-11-06**. Every modified upstream file carries an inline
notice; every change is also reproducible from the descriptors in
[`overlay/patches/`](overlay/patches/) and from the Git history.

1. Added downstream author and copyright to the generated assembly metadata
   (`scripts/Build.ps1`) and to the in-app diagnostic text
   (`scripts/TrayApp.cs`).
2. Repointed `UpdateTrust.Repository` and `UpdateTrust.ApiUrl` in
   `scripts/UpdateValidation.cs` to this repository, so the in-app source link
   and one-click updater serve this publisher's releases.
3. Replaced `UpdateTrust.PublicKeyXml` with LeoZhang's own public key, so
   releases are verified against this publisher's signature rather than the
   upstream maintainer's key.
4. Repointed the in-app source link, compatibility-document link and the
   source-checkout download hint to this repository
   (`scripts/PopupPages.cs`, `scripts/TrayApp.cs`, `scripts/Start.ps1`).
5. Added `CREDITS.md` and `FORK-README.md` to every distributed ZIP by patching
   `scripts/Package.ps1`, so the licence and change notices travel with the
   binary rather than living only on GitHub.
6. Updated three upstream test expectations that hardcoded the original
   repository URL (`tests/UpdateTests.cs`, `tests/UnadaptedDiagnosticTests.cs`,
   `tests/UiMenusTests.cs`). No test assertion was weakened.
7. Added the fork synchronization toolchain, the declarative overlay patch
   replayer, the hourly sync workflow, the signed-release workflow,
   architecture/compliance notes and the local device baseline. These are new
   files; no upstream file was deleted.

`AppId` and `ZipName` were deliberately left unchanged. The original
`LICENSE` and `THIRD_PARTY_NOTICES.md` were not modified. The feedback relay
and device-pack trust roots are intentionally left as upstream shipped them;
see `docs/fork/COMPLIANCE.md` for the open decision.

## Your rights

This derivative may be used, modified and redistributed under the terms of the
**AGPL-3.0-only**, including the network-interaction provisions of section 13.
Complete corresponding source code for every released binary is published in
this repository. No additional restrictions, EULA terms or warranty promises
are imposed on downstream recipients.

Software is provided **as is**, without warranty of any kind. Device support
marked level C in `docs/compatibility.md` means "protocol implemented, real-hardware
verification pending" and is not a compatibility guarantee.

## Attribution Summary

| Role | Party | Notice |
| --- | --- | --- |
| Original author | wushuai0802 | Copyright (C) 2026, AGPL-3.0-only |
| HaloBattery contributors | HeyOkay/HaloBattery | MIT, see `engine/licenses/` |
| Modifier & publisher | LeoZhang | Copyright (C) 2026, AGPL-3.0-only |
