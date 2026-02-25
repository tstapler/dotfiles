# GitHub Actions Debugging Examples

Step-by-step walkthroughs of complex debugging scenarios. Load this file when you need concrete examples of the debugging methodology in action.

---

## Example 1: npm Dependency Resolution Failure

### Initial Failure
```
Run npm ci
npm ERR! code ERESOLVE
npm ERR! ERESOLVE unable to resolve dependency tree
npm ERR! 
npm ERR! While resolving: my-app@1.0.0
npm ERR! Found: react@17.0.2
npm ERR! node_modules/react
npm ERR!   react@"^17.0.2" from the root project
npm ERR! 
npm ERR! Could not resolve dependency:
npm ERR! peer react@"^18.0.0" from react-awesome-library@2.0.0
npm ERR! node_modules/react-awesome-library
npm ERR!   react-awesome-library@"^2.0.0" from the root project
Error: Process completed with exit code 1.
```

### Phase 1: Context Gathering
- **Failed Job:** `build`
- **Failed Step:** `Install dependencies`
- **Runner:** `ubuntu-latest`
- **Trigger:** PR merge to main

### Phase 2: Log Analysis
Error indicates peer dependency conflict:
- Current project uses React 17
- New dependency requires React 18
- npm 7+ enforces strict peer dependencies

### Phase 3: Error Categorization
- **Category:** Dependency
- **Severity:** Critical (blocks build)
- **Type:** Deterministic

### Phase 4: Root Cause Analysis
Recent changes show `react-awesome-library` was added in package.json but React version wasn't updated:

```json
{
  "dependencies": {
    "react": "^17.0.2",
    "react-awesome-library": "^2.0.0"  // Requires React 18
  }
}
```

### Phase 5: Solution

**Root Cause:**
Added dependency requires React 18, but project still on React 17.

**Fix:**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-awesome-library": "^2.0.0"
  }
}
```

Then regenerate lock file:
```bash
rm package-lock.json
npm install
git add package.json package-lock.json
git commit -m "fix: upgrade React to v18 for react-awesome-library compatibility"
```

**Why This Works:**
Upgrades React to version compatible with all dependencies, satisfying peer dependency requirements.

**Prevention:**
- Check peer dependencies before adding packages
- Use `npm info package peerDependencies` to verify
- Keep major dependencies up to date

**Verification:**
```bash
npm ci  # Should succeed locally
# Push and verify CI passes
```

---

## Example 2: Permission Denied Pushing Docker Image

### Initial Failure
```
Run docker push ghcr.io/org/myapp:latest
denied: permission_denied: write_package
Error: Process completed with exit code 1.
```

### Phase 1: Context Gathering
- **Failed Job:** `deploy`
- **Failed Step:** `Push Docker image`
- **Runner:** `ubuntu-latest`
- **Trigger:** Push to main branch

### Phase 2: Log Analysis
Error shows permission denied when pushing to GitHub Container Registry (ghcr.io).

### Phase 3: Error Categorization
- **Category:** Permission
- **Severity:** Critical
- **Type:** Deterministic

### Phase 4: Root Cause Analysis
Workflow file shows:
```yaml
- name: Push Docker image
  run: docker push ghcr.io/org/myapp:latest
```

GITHUB_TOKEN default permissions don't include package write access.

### Phase 5: Solution

**Root Cause:**
GITHUB_TOKEN lacks `packages: write` permission needed for pushing to GitHub Container Registry.

**Fix:**
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write  # Add this
    steps:
      - uses: actions/checkout@v3
      
      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          push: true
          tags: ghcr.io/org/myapp:latest
```

**Why This Works:**
- Adds `packages: write` permission to job
- Uses proper login action with GITHUB_TOKEN
- Authenticates before pushing

**Prevention:**
- Always add permissions explicitly for package operations
- Use docker/login-action for authentication
- Document required permissions in workflow comments

**Verification:**
```bash
# Check image was pushed
gh api /user/packages/container/myapp/versions
```

---

## Example 3: Test Suite Timeout on Large Codebase

### Initial Failure
```
Run npm test
PASS src/components/Button.test.tsx
PASS src/components/Input.test.tsx
...
(2000+ test files)
...
##[error]The job running on runner GitHub Actions 2 has exceeded the maximum execution time of 360 minutes.
Error: The operation was canceled.
```

### Phase 1: Context Gathering
- **Failed Job:** `test`
- **Failed Step:** `Run tests`
- **Runner:** `ubuntu-latest`
- **Trigger:** PR
- **Context:** Large monorepo with 2000+ test files

### Phase 2: Log Analysis
Job timed out after 360 minutes (6 hours) while running Jest tests sequentially.

### Phase 3: Error Categorization
- **Category:** Timeout
- **Severity:** Critical
- **Type:** Deterministic (always fails)

### Phase 4: Root Cause Analysis
Workflow runs all tests sequentially:
```yaml
- run: npm test
```

No parallelization or caching. Tests run on single worker.

### Phase 5: Solution

**Root Cause:**
Running 2000+ test files sequentially on single worker exceeds job timeout.

**Fix - Use Matrix Strategy with Sharding:**
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        shard: [1, 2, 3, 4, 5, 6, 7, 8]
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
      
      - run: npm ci
      
      - name: Run tests (shard ${{ matrix.shard }}/8)
        run: npm test -- --shard=${{ matrix.shard }}/8 --maxWorkers=2
        timeout-minutes: 45
```

**Why This Works:**
- Splits tests into 8 parallel jobs (shards)
- Each shard runs ~250 test files
- Reduces total time from 360+ min to ~45 min per shard
- Uses npm cache to speed up dependency installation
- Sets per-step timeout to fail fast

**Prevention:**
- Use test sharding for large test suites
- Monitor test execution time trends
- Optimize slow tests
- Use cached dependencies

**Verification:**
- Each shard should complete in <45 minutes
- Total wall-clock time: ~45 minutes (parallel)
- All 8 shards must pass for PR to merge

---

## Example 4: Matrix Build Partial Failure (Windows-Specific)

### Initial Failure
```
Matrix: os=windows-latest, node=18
Run npm run build
> my-app@1.0.0 build
> webpack --mode production

Error: EPERM: operation not permitted, rename 'dist\bundle.js.tmp' -> 'dist\bundle.js'
```

All other matrix combinations (Ubuntu, macOS) passed.

### Phase 1: Context Gathering
- **Failed Job:** `build`
- **Matrix:** `os=windows-latest, node=18`
- **Other Combinations:** All passed (Ubuntu, macOS)
- **Trigger:** PR

### Phase 2: Log Analysis
Windows-specific EPERM error when webpack tries to rename temp file. This is a known Windows file locking issue.

### Phase 3: Error Categorization
- **Category:** Environment (OS-specific)
- **Severity:** Critical (blocks Windows builds)
- **Type:** Intermittent (Windows file locking race condition)

### Phase 4: Root Cause Analysis
Windows file system locks files more aggressively than Unix systems. Webpack's file writing can trigger EPERM errors when:
- Antivirus scans lock files
- File handles not released immediately
- Temp file cleanup race condition

### Phase 5: Solution

**Root Cause:**
Windows file system locking causes webpack file rename failures during parallel builds.

**Fix - Add Retry Logic and Reduce Parallelism:**
```yaml
jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        node: [16, 18, 20]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-node@v3
        with:
          node-version: ${{ matrix.node }}
      
      - run: npm ci
      
      - name: Build (Windows)
        if: runner.os == 'Windows'
        uses: nick-fields/retry@v2
        with:
          timeout_minutes: 10
          max_attempts: 3
          command: npm run build
        env:
          # Reduce webpack parallelism on Windows
          NODE_OPTIONS: --max-old-space-size=4096
      
      - name: Build (Unix)
        if: runner.os != 'Windows'
        run: npm run build
```

**Alternative Fix - Adjust webpack config:**
```javascript
// webpack.config.js
module.exports = {
  // Disable webpack's caching on Windows
  cache: process.platform === 'win32' ? false : {
    type: 'filesystem',
  },
  // Reduce parallelism on Windows
  parallelism: process.platform === 'win32' ? 1 : 100,
};
```

**Why This Works:**
- Retry logic handles intermittent file locking
- Reduced parallelism minimizes concurrent file operations
- Windows-specific configuration prevents race conditions

**Prevention:**
- Test builds on Windows locally
- Use platform-specific configurations
- Monitor for Windows-specific issues
- Consider excluding problematic matrix combinations if not critical

**Verification:**
Re-run workflow multiple times to verify Windows builds succeed consistently.

---

## Example 5: Secrets Not Available in Forked PR

### Initial Failure
```
Run aws s3 cp dist/ s3://my-bucket --recursive
fatal error: Unable to locate credentials
Error: Process completed with exit code 1.
```

Works on direct PRs, fails on forked PRs.

### Phase 1: Context Gathering
- **Failed Job:** `deploy-preview`
- **Trigger:** PR from forked repository
- **Context:** Workflow tries to deploy to S3 using secrets

### Phase 2: Log Analysis
AWS credentials not found. Secrets are not available to forked PRs for security reasons.

### Phase 3: Error Categorization
- **Category:** Permission (secrets unavailable)
- **Severity:** Expected behavior (security feature)
- **Type:** Deterministic for forks

### Phase 4: Root Cause Analysis
GitHub Actions doesn't expose secrets to workflows triggered by forked PRs to prevent secret exfiltration. Current workflow:
```yaml
on: [pull_request]

jobs:
  deploy-preview:
    runs-on: ubuntu-latest
    steps:
      - run: aws s3 cp dist/ s3://my-bucket --recursive
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

### Phase 5: Solution

**Root Cause:**
Secrets are not available to workflows triggered by forked PRs for security reasons.

**Fix - Skip deployment for forks:**
```yaml
on: [pull_request]

jobs:
  deploy-preview:
    runs-on: ubuntu-latest
    # Only run for PRs from same repo
    if: github.event.pull_request.head.repo.full_name == github.repository
    steps:
      - uses: actions/checkout@v3
      
      - run: npm run build
      
      - name: Deploy to S3
        run: aws s3 cp dist/ s3://my-bucket/pr-${{ github.event.number }}/ --recursive
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

**Alternative - Use pull_request_target (careful!):**
```yaml
# WARNING: Only use if you understand security implications
on:
  pull_request_target:  # Has access to secrets

jobs:
  deploy-preview:
    runs-on: ubuntu-latest
    steps:
      # CRITICAL: Check out PR code in isolated step
      - uses: actions/checkout@v3
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      
      # Build in isolated environment (no secrets)
      - run: npm ci
      - run: npm run build
      
      # Only expose secrets to trusted deployment step
      - name: Deploy
        run: aws s3 cp dist/ s3://my-bucket --recursive
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

**Why This Works:**
- First approach skips deployment for forked PRs (safe)
- Second approach uses `pull_request_target` which has secret access but requires careful security review

**Prevention:**
- Document fork PR limitations
- Use conditions to skip secret-dependent steps for forks
- Consider separate workflow for fork PRs (build only)
- Use pull_request_target only when necessary and with security review

**Verification:**
- Test with fork PR (should skip deployment or build only)
- Test with same-repo PR (should deploy)

---

## Example 6: Cache Restoration Failure After Dependency Update

### Initial Failure
```
Run actions/cache@v3
Cache not found for input keys: node-modules-${{ hashFiles('**/package-lock.json') }}
...
Run npm ci
(Takes 5+ minutes instead of usual 30 seconds)
```

Build succeeds but much slower than usual.

### Phase 1: Context Gathering
- **Failed Step:** `Restore cache`
- **Impact:** Build time increased from 2min to 7min
- **Trigger:** PR updating dependencies
- **Context:** package-lock.json was modified

### Phase 2: Log Analysis
Cache key uses hash of package-lock.json. After dependency update, hash changed, invalidating cache.

### Phase 3: Error Categorization
- **Category:** Performance (not a failure, but degraded)
- **Severity:** Warning
- **Type:** Expected behavior after dependency changes

### Phase 4: Root Cause Analysis
Workflow uses exact cache key:
```yaml
- uses: actions/cache@v3
  with:
    path: ~/.npm
    key: node-modules-${{ hashFiles('**/package-lock.json') }}
```

No restore-keys specified, so when package-lock.json changes, cache completely missed.

### Phase 5: Solution

**Root Cause:**
Cache key based on package-lock.json hash invalidates completely on dependency updates. No fallback strategy.

**Fix - Add restore-keys for partial matches:**
```yaml
- uses: actions/cache@v3
  with:
    path: ~/.npm
    key: node-modules-${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      node-modules-${{ runner.os }}-
```

**Better - Use actions/setup-node built-in caching:**
```yaml
- uses: actions/setup-node@v3
  with:
    node-version: '18'
    cache: 'npm'  # Automatically handles caching
```

**Why This Works:**
- `restore-keys` allows partial cache hits when exact key misses
- Restores most recent cache even if package-lock.json changed
- npm ci only reinstalls changed packages
- setup-node's cache handles this automatically

**Prevention:**
- Always use restore-keys with cache
- Use built-in caching features when available
- Monitor cache hit rates
- Expect cache misses after dependency updates (normal)

**Verification:**
- First run after change: cache miss (expected)
- Subsequent runs: cache hit
- Build time returns to normal

---

## Example 7: Composite Action Input Validation Failure

### Initial Failure
```
Run ./.github/actions/deploy
Error: Input required and not supplied: environment
Error: Required input 'environment' not provided
```

### Phase 1: Context Gathering
- **Failed Step:** Custom composite action
- **Action:** `./.github/actions/deploy`
- **Trigger:** Workflow using composite action

### Phase 2: Log Analysis
Composite action expects `environment` input but workflow didn't provide it.

Action definition (action.yml):
```yaml
name: Deploy
inputs:
  environment:
    required: true
    description: 'Deployment environment'
runs:
  using: composite
  steps:
    - run: echo "Deploying to ${{ inputs.environment }}"
```

Workflow usage:
```yaml
- uses: ./.github/actions/deploy
  # Missing: with.environment
```

### Phase 3: Error Categorization
- **Category:** Syntax/Configuration
- **Severity:** Critical
- **Type:** Deterministic

### Phase 4: Root Cause Analysis
Workflow author didn't provide required input when calling composite action.

### Phase 5: Solution

**Root Cause:**
Required input `environment` not provided to composite action.

**Fix - Provide required input:**
```yaml
- uses: ./.github/actions/deploy
  with:
    environment: production
```

**Better - Make input optional with default:**
```yaml
# .github/actions/deploy/action.yml
inputs:
  environment:
    required: false
    default: 'staging'
    description: 'Deployment environment'
```

**Why This Works:**
- Provides required input to action
- Or makes input optional with sensible default

**Prevention:**
- Document required inputs in action README
- Use input validation in composite actions
- Provide helpful error messages
- Consider defaults for optional inputs

**Verification:**
```bash
# Test composite action locally
act -j deploy
```

---

## Summary

These examples demonstrate:
- **Systematic approach** to debugging across error categories
- **Root cause analysis** beyond surface-level symptoms
- **Multiple solution strategies** with tradeoffs
- **Prevention measures** to avoid recurring issues
- **Verification steps** to confirm fixes work

Apply the same 5-phase methodology to any GitHub Actions failure for consistent, efficient debugging.
