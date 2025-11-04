# Local Docker Testing Requirements

## Prerequisites for Local Development

### 1. Docker Desktop

Install Docker Desktop for your platform:
- **macOS**: Download from https://www.docker.com/products/docker-desktop
- **Linux**: Follow distribution-specific instructions
- **Windows**: Docker Desktop with WSL2

**Verification:**
```bash
docker --version
docker info  # Should show running daemon
```

### 2. Make (Built-in on macOS/Linux)

Make sure `make` is available:
```bash
make --version
```

### 3. AWS CLI (Optional - only for pushing to ECR)

```bash
# macOS
brew install awscli

# Verify
aws --version
```

## Mandatory Local Testing Workflow

**CRITICAL**: Always test Docker builds locally before pushing to prevent CI/CD failures.

### Using Makefile (Recommended)

```bash
# Complete validation pipeline (recommended before any push)
make validate

# Build and test everything
make all

# Build individual images
make build-healthcheck    # Build healthcheck image only
make build-pgbouncer     # Build PGBouncer image only

# Test individual images
make test-healthcheck    # Test healthcheck functionality
make test-pgbouncer      # Test PGBouncer functionality

# Show image information
make info

# Clean up local images
make clean
```

### Manual Docker Testing (Fallback)

If you prefer direct Docker commands:

```bash
# Build images
docker build -f Dockerfile.healthcheck -t pgbouncer-healthcheck:latest .
docker build -f Dockerfile.pgbouncer -t pgbouncer:latest .

# Test functionality
docker run --rm pgbouncer-healthcheck:latest /usr/local/bin/healthcheck-unified.py --help
docker run --rm pgbouncer:latest /usr/local/bin/pgbouncer --version

# Check image sizes
docker images | grep -E "(pgbouncer-healthcheck|pgbouncer)"
```

### Pre-Push Checklist

Before pushing any Docker-related changes:

1. ✅ **Run complete validation** - must succeed
   ```bash
   make validate
   ```

2. ✅ **Check build output** - no errors or warnings
   ```bash
   make build 2>&1 | grep -i error
   ```

3. ✅ **Verify functionality** - smoke tests pass
   ```bash
   make test
   ```

4. ✅ **Check image sizes** - verify optimization
   ```bash
   make info
   ```

5. ✅ **Clean validation** - start fresh
   ```bash
   make clean && make validate
   ```

### Makefile Commands Reference

```bash
# 🎯 Primary workflows
make validate         # Complete validation pipeline (BUILD + TEST + INFO)
make all              # Build and test both images
make build            # Build both images
make test             # Test both images

# 🏗️ Build commands
make build-healthcheck # Build healthcheck image only
make build-pgbouncer  # Build PGBouncer image only

# 🧪 Test commands
make test-healthcheck # Test healthcheck image only
make test-pgbouncer   # Test PGBouncer image only

# 🚀 Push commands (requires AWS auth)
make push             # Push both images to ECR
make push-healthcheck # Push healthcheck image to ECR
make push-pgbouncer   # Push PGBouncer image to ECR

# 🛠️ Utility commands
make info             # Show image information and sizes
make clean            # Remove local images
make clean-all        # Deep clean everything including ECR tags
make debug            # Build with verbose debugging output
make check            # Check prerequisites (Docker, AWS CLI)
make help             # Show detailed help
```

### Troubleshooting Local Builds

#### Common Issues

- **Docker daemon not running**: Start Docker Desktop
- **Permission denied**: Ensure user has Docker access (`docker info`)
- **Build failures**: Use `make debug` for verbose output
- **Disk space**: Use `make clean-all` to free up space

#### Build Failure Debugging

```bash
# Verbose debugging mode
make debug

# Check prerequisites
make check

# Clean and rebuild
make clean && make build

# Build with no cache
docker build --no-cache -f Dockerfile.pgbouncer -t pgbouncer:debug .

# Check individual layers
docker history pgbouncer:latest
```

#### Docker + Make Advantages

- ✅ **Simple and reliable** - standard Docker workflow everyone knows
- ✅ **No complex tooling** - just Docker + Make (built-in)
- ✅ **Easy debugging** - familiar Docker commands and logs
- ✅ **CI/CD compatible** - same commands work locally and in pipelines
- ✅ **Comprehensive validation** - complete pre-push checklist
