---
name: android-versioning
description: "Use this skill when setting up or explaining Android versionCode/versionName for KMP or standard Android projects. Implements packed semver: major*1_000_000 + minor*1_000 + patch as a single integer that preserves semver ordering."
---

# Android Versioning — Packed SemVer

Android requires `versionCode` as a single integer, but we encode `major.minor.patch` into it using place-value arithmetic so semver ordering is preserved.

## Formula

```
versionCode = major * 1_000_000 + minor * 1_000 + patch
```

Examples: `v1.3.0` → `1_003_000`, `v1.2.999` → `1_002_999`. Since `1_003_000 > 1_002_999`, ordering is always correct.

**Limits:** major 0–2100, minor 0–999, patch 0–999 (Android cap: 2,100,000,000).

**Gotcha:** If minor or patch exceeds 999, they bleed into the next component's space and break ordering. In practice this never happens.

## Gradle Implementation

In `androidApp/build.gradle.kts` inside `defaultConfig {}`:

```kotlin
val appVersionStr = (findProperty("appVersion") as? String ?: "0.1.0").removePrefix("v")
val vParts = appVersionStr.split(".")
val vMajor = vParts.getOrNull(0)?.toIntOrNull() ?: 0
val vMinor = vParts.getOrNull(1)?.toIntOrNull() ?: 0
val vPatch = vParts.getOrNull(2)?.toIntOrNull() ?: 0
versionCode = (vMajor * 1_000_000 + vMinor * 1_000 + vPatch).coerceAtLeast(2)
versionName = appVersionStr
```

- CI passes `-PappVersion=X.Y.Z` to Gradle; local builds fall back to `"0.1.0"`.
- `coerceAtLeast(2)`: ensures every new APK outranks historical builds that used the hardcoded `versionCode = 1` default.

## CI Strategy

### Dev builds (every push to main)

Derive version automatically: latest git tag sets major.minor; commits since that tag become patch.

```bash
BASE_TAG=$(git describe --tags --match "v*" --abbrev=0 2>/dev/null || echo "v0.1.0")
BASE_VER=${BASE_TAG#v}
MAJOR=$(echo "$BASE_VER" | cut -d. -f1)
MINOR=$(echo "$BASE_VER" | cut -d. -f2)
PATCH=$(git rev-list "${BASE_TAG}..HEAD" --count 2>/dev/null || echo "0")
APP_VERSION="${MAJOR}.${MINOR}.${PATCH}"
echo "APP_VERSION=${APP_VERSION}" >> $GITHUB_ENV
```

Then pass `-PappVersion="$APP_VERSION"` to both `assembleRelease` and `appDistributionUploadRelease`.

### Prod builds (manual workflow dispatch)

Require an exact tag on HEAD — fail loudly if missing:

```bash
APP_VERSION=$(git describe --tags --exact-match HEAD 2>/dev/null | sed 's/^v//')
if [ -z "$APP_VERSION" ]; then
  echo "ERROR: HEAD is not tagged. Tag a release with 'git tag vX.Y.Z && git push --tags' before deploying to prod."
  exit 1
fi
echo "APP_VERSION=${APP_VERSION}" >> $GITHUB_ENV
```

## Release Notes

Run this step before `appDistributionUploadRelease`:

```bash
{
  echo "v${APP_VERSION} · $(date -u '+%Y-%m-%d %H:%M UTC')"
  echo "Commit: $GITHUB_SHA"
  echo ""
  git log --oneline -15 --format="• %s"
} > androidApp/release-notes.txt
```

## Bumping Major / Minor

```bash
git tag v0.2.0
git push --tags
# Then trigger the prod deploy workflow
```

Patch auto-increments on every dev build; you only tag when intentionally cutting a minor or major release.
