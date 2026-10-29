# JARVIS Platform Version Register

This is the permanent index for version history. Android and PC are tracked independently.

## Android / Mobile
- Configured versionName: `0.13.0`
- Configured versionCode: `13`
- Source: [android/app/build.gradle.kts](android/app/build.gradle.kts)
- CI artifact name: `JARVIS-Android-v0.13.0`
- Latest release commit SHA: **Not yet verified**
- Latest CI run / test status: **Not yet verified**
- History: [CHANGELOG-MOBILE.md](CHANGELOG-MOBILE.md)

## PC / Windows
- Desktop version: **Needs its own version identifier; do not assume it matches Android**
- CI artifact name: `jarvis-desktop-windows`
- Latest release commit SHA: **Not yet verified**
- Latest CI run / test status: **Not yet verified**
- History: [CHANGELOG-PC.md](CHANGELOG-PC.md)
- Source: [desktop/main.py](desktop/main.py)

## Linux Desktop
- CI artifact name: `jarvis-desktop-linux`
- Track independently if Linux releases are published.

## Required record for every release
Record platform, version, full commit SHA, commit URL, workflow-run URL, artifact name/download location, test results, changes, and known issues.

**Important:** a CI artifact is a build, not automatically a tested release. Mark a release tested only after inspecting its workflow run and test results. Never invent versions, SHAs, or test status.
