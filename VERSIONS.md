# JARVIS Platform Version Register

Track Android and PC independently. A CI build is not automatically a published release.

## Android / Mobile
- Configured versionName: `0.13.0`
- Configured versionCode: `13`
- Version source: [android/app/build.gradle.kts](android/app/build.gradle.kts)
- Verified CI artifact: `JARVIS-Android-v0.13.0`
- Artifact ID: `12814167575` (run 40683955777)
- Build commit: [`6f7f13545c46bcf8097245d471202e4393152975`](https://github.com/REDLINE-INTERACTIVE-DEV/JARVIS/commit/6f7f13545c46bcf8097245d471202e4393152975)
- CI run: [#40683955777](https://github.com/REDLINE-INTERACTIVE-DEV/JARVIS/actions/runs/40683955777)
- CI job status: Android job succeeded, including debug APK build, unit tests, and APK signature verification.
- Platform history: [CHANGELOG-MOBILE.md](CHANGELOG-MOBILE.md)

## PC / Windows
- Desktop version identifier: **Not independently configured/verified yet**; do not copy Android's version number.
- Verified CI artifact: `jarvis-desktop-windows`
- Artifact ID: `12813223863` (run 40683955777)
- Build commit: [`6f7f13545c46bcf8097245d471202e4393152975`](https://github.com/REDLINE-INTERACTIVE-DEV/JARVIS/commit/6f7f13545c46bcf8097245d471202e4393152975)
- CI run: [#40683955777](https://github.com/REDLINE-INTERACTIVE-DEV/JARVIS/actions/runs/40683955777)
- CI job status: Windows packaging job succeeded; PyInstaller created the executable and uploaded the artifact. This confirms packaging, not a manual launch test on your laptop.
- Platform history: [CHANGELOG-PC.md](CHANGELOG-PC.md)
- Source: [desktop/main.py](desktop/main.py)

## Linux Desktop
- Verified CI artifact: `jarvis-desktop-linux`
- Artifact ID: `12813522728` (run 40683955777)
- CI run: [#40683955777](https://github.com/REDLINE-INTERACTIVE-DEV/JARVIS/actions/runs/40683955777)

## Tracking register commit
- Commit adding the initial register: [`c1da842737da677f6e900dba01cc7a439e2057d7`](https://github.com/REDLINE-INTERACTIVE-DEV/JARVIS/commit/c1da842737da677f6e900dba01cc7a439e2057d7)
- Rule: every new platform build must record its own version, full commit SHA, workflow URL, artifact ID/name, CI test results, changes, and known issues. Never invent missing values.
