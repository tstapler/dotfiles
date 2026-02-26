# Comprehensive GitHub Actions Error Patterns

This file provides detailed error patterns, root causes, and solutions for GitHub Actions debugging. Load this when the Quick Reference table in SKILL.md is insufficient.

---

## Syntax & Configuration Errors

### YAML Syntax Errors

**Error Signature:**
```
Error: .github/workflows/ci.yml (Line: X, Col: Y): Unexpected token
YAML syntax error
Invalid workflow file
```

**Root Causes:**
- Incorrect indentation (mixing tabs and spaces)
- Missing quotes around special characters
- Invalid character in key names
- Unclosed brackets/braces
- Missing colons after keys

**Fixes:**
1. Run `yamllint .github/workflows/` to identify syntax issues
2. Use 2-space indentation consistently (no tabs)
3. Quote strings containing `:`, `{`, `}`, `[`, `]`, `,`, `&`, `*`, `#`, `?`, `|`, `-`, `<`, `>`, `=`, `!`, `%`, `@`, `` ` ``
4. Validate online: https://www.yamllint.com/

**Prevention:**
- Use editor with YAML syntax highlighting
- Install yamllint pre-commit hook
- Use GitHub Actions extension in VS Code

---

### Invalid Workflow Schema

**Error Signature:**
```
Invalid workflow file: .github/workflows/X.yml#L10
The workflow is not valid. .github/workflows/X.yml (Line: 10, Col: 3): Unexpected value 'X'
```

**Root Causes:**
- Missing required fields (name, on, jobs)
- Invalid action input names
- Incorrect job dependency in `needs`
- Invalid trigger event names
- Wrong context variable syntax

**Fixes:**
1. Verify required top-level keys exist:
   ```yaml
   name: My Workflow
   on: [push]
   jobs:
     build:
       runs-on: ubuntu-latest
       steps: []
   ```

2. Check action inputs match action.yml definition
3. Validate `needs` references existing job names
4. Use correct trigger events: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows
5. Use `${{ }}` syntax for expressions

**Prevention:**
- Use schema validation in editor
- Reference official docs for each action
- Test workflows in forked repos first

---

## Dependency Errors

### npm - Peer Dependency Conflicts

**Error Signature:**
```
npm ERR! code ERESOLVE
npm ERR! ERESOLVE unable to resolve dependency tree
npm ERR! Could not resolve dependency:
npm ERR! peer X@"Y" from Z@A
```

**Root Causes:**
- Package requires incompatible peer dependency versions
- Lock file generated with different npm version
- Transitive dependency conflicts
- Strict peer dependency resolution in npm 7+

**Fixes:**
1. **Quick fix** (not recommended for production):
   ```yaml
   - run: npm install --legacy-peer-deps
   ```

2. **Proper fix**:
   ```yaml
   - run: npm install --force
   # or
   - run: |
       npm config set legacy-peer-deps true
       npm ci
   ```

3. **Best fix** - Update package.json:
   ```json
   {
     "overrides": {
       "problematic-package": "compatible-version"
     }
   }
   ```

**Prevention:**
- Pin npm version in workflow
- Commit package-lock.json
- Use `npm ci` instead of `npm install`
- Keep dependencies updated regularly

---

### npm - Lock File Out of Sync

**Error Signature:**
```
npm ERR! code EUSAGE
npm ERR! `npm ci` can only install packages when your package.json and package-lock.json are in sync
npm ERR! Please update your lock file with `npm install` before continuing.
```

**Root Causes:**
- package.json modified without updating lock file
- Lock file generated with different npm version
- Manual lock file edits
- Merge conflict resolution errors

**Fixes:**
1. Regenerate lock file:
   ```bash
   rm package-lock.json
   npm install
   git add package-lock.json
   git commit -m "fix: regenerate lock file"
   ```

2. Update workflow to use npm install:
   ```yaml
   - run: npm install
   # Instead of npm ci temporarily
   ```

**Prevention:**
- Always run `npm install` after changing package.json
- Commit lock file changes with dependency changes
- Use `npm ci` in CI/CD (enforces sync check)
- Pin npm version in workflow

---

### Python - pip Dependency Resolution

**Error Signature:**
```
ERROR: Cannot install X because these package versions have incompatible dependencies.
ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/latest/topics/dependency-resolution
```

**Root Causes:**
- Conflicting version requirements
- Package not available for Python version
- Platform-specific dependency issues
- pip resolver cannot find compatible versions

**Fixes:**
1. Pin conflicting packages explicitly:
   ```txt
   # requirements.txt
   package-a==1.2.3
   package-b==4.5.6  # Compatible with package-a
   ```

2. Use constraint files:
   ```yaml
   - run: pip install -r requirements.txt -c constraints.txt
   ```

3. Upgrade pip resolver:
   ```yaml
   - run: python -m pip install --upgrade pip setuptools wheel
   ```

4. Use virtual environment isolation:
   ```yaml
   - run: |
       python -m venv venv
       source venv/bin/activate
       pip install -r requirements.txt
   ```

**Prevention:**
- Use requirements.txt with pinned versions
- Test with same Python version locally
- Use dependency management tools (poetry, pipenv)
- Commit lock files (poetry.lock, Pipfile.lock)

---

### Go - Module Inconsistencies

**Error Signature:**
```
go: inconsistent vendoring in /home/runner/work/repo/repo:
go: inconsistent vendoring
```

**Root Causes:**
- go.mod and vendor/ out of sync
- Missing vendor directory
- go.sum verification failure
- Dependency version mismatch

**Fixes:**
1. Regenerate vendor directory:
   ```yaml
   - run: |
       go mod tidy
       go mod vendor
   ```

2. Update go.sum:
   ```yaml
   - run: go mod download
   ```

3. Disable vendoring:
   ```yaml
   - run: go build -mod=mod ./...
   ```

**Prevention:**
- Commit vendor/ directory or exclude it consistently
- Run `go mod tidy` before committing
- Use same Go version locally and in CI
- Enable Go modules checksum database

---

## Permission Errors

### Token Insufficient Permissions

**Error Signature:**
```
Error: Resource not accessible by integration
Error: HttpError: Resource not accessible by integration
```

**Root Causes:**
- GITHUB_TOKEN lacks required permissions
- Default token permissions too restrictive
- Organization security policy restrictions
- Token not passed to composite action

**Fixes:**
1. Add permissions to workflow:
   ```yaml
   permissions:
     contents: write
     pull-requests: write
     issues: write
   ```

2. Add permissions to specific job:
   ```yaml
   jobs:
     deploy:
       permissions:
         contents: write
       runs-on: ubuntu-latest
   ```

3. Use PAT instead of GITHUB_TOKEN:
   ```yaml
   - uses: actions/checkout@v3
     with:
       token: ${{ secrets.PAT_TOKEN }}
   ```

**Prevention:**
- Use least-privilege principle
- Document required permissions in README
- Test with default token permissions first
- Check org settings for token restrictions

---

### SSH Authentication Failures

**Error Signature:**
```
Permission denied (publickey)
fatal: Could not read from remote repository
Host key verification failed
```

**Root Causes:**
- SSH key not configured in repository
- Wrong SSH key used
- Host key verification failure
- SSH agent not running

**Fixes:**
1. Use HTTPS with token instead:
   ```yaml
   - uses: actions/checkout@v3
     with:
       token: ${{ secrets.GITHUB_TOKEN }}
   ```

2. Configure SSH key:
   ```yaml
   - uses: webfactory/ssh-agent@v0.7.0
     with:
       ssh-private-key: ${{ secrets.SSH_PRIVATE_KEY }}
   ```

3. Disable host key checking (not recommended):
   ```yaml
   - run: |
       mkdir -p ~/.ssh
       echo "StrictHostKeyChecking no" >> ~/.ssh/config
   ```

**Prevention:**
- Prefer HTTPS over SSH in CI/CD
- Use deploy keys for repository access
- Document SSH key setup requirements
- Rotate SSH keys regularly

---

### SAML SSO Authorization

**Error Signature:**
```
Error: HttpError: Resource protected by organization SAML enforcement
```

**Root Causes:**
- Personal access token not authorized for SAML SSO
- Token created before SAML enforcement
- Organization security policy change

**Fixes:**
1. Authorize token for SSO:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Find the token
   - Click "Configure SSO" → "Authorize" for organization

2. Create new token with SSO authorization:
   ```yaml
   # Use newly created and authorized token
   - uses: actions/checkout@v3
     with:
       token: ${{ secrets.SAML_AUTHORIZED_TOKEN }}
   ```

**Prevention:**
- Authorize tokens for SSO immediately after creation
- Document SSO requirement in workflow README
- Use GitHub Apps instead of PATs when possible
- Audit token authorizations regularly

---

## Timeout & Resource Errors

### Job Timeout

**Error Signature:**
```
##[error]The job running on runner X has exceeded the maximum execution time of 360 minutes.
Error: The operation was canceled.
```

**Root Causes:**
- Long-running tests or builds
- Infinite loops or hangs
- Waiting for external service
- Default timeout too short for job

**Fixes:**
1. Increase job timeout:
   ```yaml
   jobs:
     build:
       timeout-minutes: 120  # Default is 360
       runs-on: ubuntu-latest
   ```

2. Increase step timeout:
   ```yaml
   - name: Run tests
     timeout-minutes: 30
     run: npm test
   ```

3. Optimize slow operations:
   - Use caching for dependencies
   - Parallelize tests
   - Split into multiple jobs
   - Use faster runners

**Prevention:**
- Set appropriate timeouts for each job
- Monitor job duration trends
- Optimize test suite performance
- Use matrix builds for parallelization

---

### Out of Memory (OOM)

**Error Signature:**
```
##[error]Process completed with exit code 137
Killed
npm ERR! errno 137
```

**Root Causes:**
- Process exceeded available memory (7GB on standard runners)
- Memory leak in tests or build
- Large file processing
- Too many parallel processes

**Fixes:**
1. Increase Node.js memory:
   ```yaml
   - run: export NODE_OPTIONS="--max-old-space-size=6144"
   - run: npm run build
   ```

2. Reduce parallelism:
   ```yaml
   - run: npm test -- --maxWorkers=2
   ```

3. Use larger runner:
   ```yaml
   jobs:
     build:
       runs-on: ubuntu-latest-8-cores  # Requires GitHub Team/Enterprise
   ```

4. Split job into smaller pieces:
   ```yaml
   strategy:
     matrix:
       shard: [1, 2, 3, 4]
   steps:
     - run: npm test -- --shard=${{ matrix.shard }}/4
   ```

**Prevention:**
- Monitor memory usage in CI
- Fix memory leaks in code
- Use streaming for large files
- Optimize build configuration

---

## Environment Errors

### Missing Tool or Command

**Error Signature:**
```
Error: Unable to locate executable file: X
/bin/bash: X: command not found
```

**Root Causes:**
- Tool not pre-installed on runner
- Wrong runner image
- PATH not configured
- Tool installation failed

**Fixes:**
1. Use setup action:
   ```yaml
   - uses: actions/setup-node@v3
     with:
       node-version: '18'
   - uses: actions/setup-python@v4
     with:
       python-version: '3.11'
   ```

2. Install tool manually:
   ```yaml
   - run: |
       sudo apt-get update
       sudo apt-get install -y tool-name
   ```

3. Use container with tool pre-installed:
   ```yaml
   jobs:
     build:
       runs-on: ubuntu-latest
       container: node:18-alpine
   ```

**Prevention:**
- Check runner software: https://github.com/actions/runner-images
- Use setup actions for language runtimes
- Document custom tool requirements
- Use containers for complex environments

---

### Missing Files or Directories

**Error Signature:**
```
ENOENT: no such file or directory, open 'X'
Error: File not found: X
```

**Root Causes:**
- File not checked out
- Wrong working directory
- Previous step failed silently
- File path case sensitivity (Linux vs. Windows)

**Fixes:**
1. Ensure checkout step exists:
   ```yaml
   - uses: actions/checkout@v3
   ```

2. Set correct working directory:
   ```yaml
   - run: npm install
     working-directory: ./frontend
   ```

3. Check file exists before using:
   ```yaml
   - run: |
       if [ ! -f "config.json" ]; then
         echo "config.json not found"
         exit 1
       fi
   ```

**Prevention:**
- Always use actions/checkout first
- Use relative paths from repository root
- Add file existence checks
- Test on same OS as runner

---

## Network & External Service Errors

### DNS Resolution Failures

**Error Signature:**
```
curl: (6) Could not resolve host: example.com
getaddrinfo ENOTFOUND example.com
```

**Root Causes:**
- Temporary DNS issue
- Service outage
- Network connectivity problem
- Firewall blocking DNS

**Fixes:**
1. Add retry logic:
   ```yaml
   - uses: nick-fields/retry@v2
     with:
       timeout_minutes: 10
       max_attempts: 3
       command: curl https://example.com
   ```

2. Use alternative DNS:
   ```yaml
   - run: |
       echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
   ```

3. Check service status before proceeding:
   ```yaml
   - run: |
       until curl -f https://api.example.com/health; do
         echo "Waiting for service..."
         sleep 5
       done
   ```

**Prevention:**
- Implement retry mechanisms
- Monitor external service dependencies
- Use health checks before integration tests
- Have fallback strategies

---

### Rate Limiting

**Error Signature:**
```
Error: API rate limit exceeded
Error: You have exceeded a secondary rate limit
403 Forbidden
```

**Root Causes:**
- Too many API requests in short time
- Shared runner IP rate limited
- GitHub API secondary rate limits
- Missing authentication

**Fixes:**
1. Add authentication:
   ```yaml
   - run: |
       curl -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
         https://api.github.com/repos/owner/repo
   ```

2. Add delays between requests:
   ```yaml
   - run: |
       for repo in $REPOS; do
         gh api repos/$repo
         sleep 2
       done
   ```

3. Use GraphQL instead of REST (fewer requests):
   ```yaml
   - run: |
       gh api graphql -f query='...'
   ```

**Prevention:**
- Authenticate all API requests
- Cache API responses
- Batch operations when possible
- Monitor rate limit headers

---

## Docker & Container Errors

### Docker Build Failures

**Error Signature:**
```
Error: buildx failed with: ERROR: failed to solve
ERROR [internal] load metadata for docker.io/library/X
COPY failed: file not found
```

**Root Causes:**
- Invalid base image or tag
- File path incorrect in COPY/ADD
- Build context doesn't include files
- Multi-stage build reference error

**Fixes:**
1. Verify base image exists:
   ```dockerfile
   FROM node:18-alpine  # Use specific tag
   ```

2. Fix COPY paths:
   ```dockerfile
   # Ensure files are in build context
   COPY package*.json ./
   COPY . .
   ```

3. Set correct build context:
   ```yaml
   - run: docker build -t myapp:latest .
     # Context is current directory
   ```

4. Debug build context:
   ```yaml
   - run: docker build --progress=plain --no-cache -t myapp .
   ```

**Prevention:**
- Use specific image tags (not :latest)
- Test Dockerfile locally first
- Use .dockerignore to exclude files
- Validate multi-stage build references

---

## Matrix Build Errors

### Partial Matrix Failures

**Error Signature:**
```
Some jobs in the matrix failed
Error in matrix combination: os=windows-latest, node=14
```

**Root Causes:**
- Platform-specific bugs
- Version incompatibilities
- Different default tools per OS
- Path separator differences

**Fixes:**
1. Add conditional steps:
   ```yaml
   - name: Windows-specific setup
     if: runner.os == 'Windows'
     run: |
       # Windows commands
   ```

2. Use cross-platform commands:
   ```yaml
   - run: npm ci  # Works on all platforms
     # Instead of platform-specific commands
   ```

3. Exclude failing combinations:
   ```yaml
   strategy:
     matrix:
       os: [ubuntu-latest, windows-latest, macos-latest]
       node: [14, 16, 18]
       exclude:
         - os: windows-latest
           node: 14
   ```

**Prevention:**
- Test locally on target platforms
- Use cross-platform tools
- Document platform-specific requirements
- Use continue-on-error for non-critical combinations
