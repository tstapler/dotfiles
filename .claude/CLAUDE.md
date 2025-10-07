# Enhanced Claude Project Instructions

## Automatic Activation
These instructions are automatically active for all conversations in this project. All available tools (Sequential Thinking, Brave Search, Puppeteer, REPL/Analysis, and Artifacts) should be utilised as needed without requiring explicit activation.

## Default Workflow
Every new conversation should automatically begin with Sequential Thinking to determine which other tools are needed for the task at hand.

## MANDATORY TOOL USAGE
- Sequential Thinking must be used for all multi-step problems or research tasks
- Brave Search must be used for any fact-finding or research queries
- Puppeteer must be used when web verification or deep diving into specific sites is needed
- REPL/Analysis must be used for any data processing or calculations
- Knowledge Graph should store important findings that might be relevant across conversations
- Artifacts must be created for all substantial code, visualizations, or long-form content

## Source Documentation Requirements
- All search results must include full URLs and titles
- Screenshots should include source URLs and timestamps
- Data sources must be clearly cited with access dates
- Knowledge Graph entries should maintain source links
- All findings should be traceable to original sources
- Brave Search results should preserve full citation metadata
- External content quotes must include direct source links

## Core Workflow

### 1. INITIAL ANALYSIS (Sequential Thinking)
- Break down the research query into core components
- Identify key concepts and relationships
- Plan search and verification strategy
- Determine which tools will be most effective

### 2. PRIMARY SEARCH (Brave Search)
- Start with broad context searches
- Use targeted follow-up searches for specific aspects
- Apply search parameters strategically (count, offset)
- Document and analyze search results

### 3. DEEP VERIFICATION (Puppeteer)
- Navigate to key websites identified in search
- Take screenshots of relevant content
- Extract specific data points
- Click through and explore relevant links
- Fill forms if needed for data gathering

### 4. DATA PROCESSING
- Use the analysis tool (REPL) for complex calculations
- Process any CSV files or structured data
- Create visualisations when helpful
- Store important findings in knowledge graph if persistent storage needed

### 5. SYNTHESIS & PRESENTATION
- Combine findings from all tools
- Present information in structured format
- Create artifacts for code, visualizations, or documents
- Highlight key insights and relationships

## Tool-Specific Guidelines

### BRAVE SEARCH
- **CRITICAL RATE LIMIT**: Brave Search has a 1 per second rate limit. NEVER make consecutive brave search calls - always either sleep 1+ seconds between calls OR run a different command in between
- Use count parameter for result volume control
- Apply offset for pagination when needed
- Combine multiple related searches
- Document search queries for reproducibility
- Include full URLs, titles, and descriptions in results
- Note search date and time for each query
- Track and cite all followed search paths
- Preserve metadata from search results

### PUPPETEER
- Take screenshots of key evidence
- Use selectors precisely for interaction
- Handle navigation errors gracefully
- Document URLs and interaction paths
- Always verify that you successfully arrived at the correct page, and received the information you were looking for, if not try again 

### SEQUENTIAL THINKING
- Always break complex tasks into manageable steps
- Document thought process clearly
- Allow for revision and refinement
- Track branches and alternatives

### REPL/ANALYSIS
- Use for complex calculations
- Process and analyse data files
- Verify numerical results
- Document analysis steps

### ARTIFACTS
- Create for substantial code pieces
- Use for visualisations
- Document file operations
- Store long-form content

## Implementation Notes
- Tools should be used proactively without requiring user prompting
- Multiple tools can and should be used in parallel when appropriate
- Each step of analysis should be documented
- Complex tasks should automatically trigger the full workflow
- 
## Python
- Always use uv for installing and manipulating python dependencies

## Python Development Guidelines
- #### **Base Instructions**
- **Adhere to All Guidelines:** Follow these rules for the entire session when writing Python code.
- **Define Dependencies with PEP 723:**
  
  ```
  python
  
  Copy code
  
  # /// script
  # requires-python = ">=3.11"
  # dependencies = [
  #   "requests<3",
  #   "rich",
  # ]
  # ///
  ```
- **Library Usage:**
    - **Default:** Use built-in libraries (e.g., `argparse`, `dataclasses`) for portability in simple scripts.
    - **With Dependencies:** If dependencies are preferred, confirm with me. Then:
        - Use `Pydantic` for Data Transfer Objects (DTOs), including field documentation.
        - Use `Literal` for string enums.
        - Provide constructors for typed DTO creation.
        - Use `Typer` for building user-friendly command-line interfaces.
- #### **Code Quality**
- **Type Annotations:**
    - Annotate all function arguments and return types.
    - Use default values for optional parameters.
- **Comments & Documentation:**
    - Comment only when the code isn't self-explanatory.
    - Write clear docstrings for functions and modules, detailing their purpose, parameters, and usage.
- **Style:**
    - Follow PEP 8 standards, allowing line lengths up to 120 characters.
    - Use Black for consistent code formatting.
    - Clearly mark any unfinished code sections.
- #### **Code Structure**
- **Separation of Concerns:**
    - Isolate UI and IO from business logic to enhance testability and maintenance.
- **Facade Pattern:**
    - For API or networking libraries, implement a facade named "service."
- **Data Models:**
    - Use classes for DTOs and Domain Objects with `dataclasses` or `Pydantic` (if using dependencies).
    - Define DTOs with built-in methods for common tasks.
    - Use DTOs for function arguments and return values.
- #### **Extras**
- **API Clients:**
    - Support pagination where necessary.
    - Use class-based structures (e.g., `GithubClient`).
    - Expose configurable options during class initialization.
- **Testing:**
    - Write pytest parametrized tests in separate files.
    - Focus on edge cases.
    - Use `dataclasses` for test data, avoiding names that start with 'Test'.
    - Use `ids=lambda testcase.description` for descriptive test names.
    - When creating benchmarks use the pytest-benchmark tool to run them and configure them with the benchmark mark

## Git Guidelines
- Only push the specific branch that you're working on.

## Code Editing
- Use the serena mcp server for editing and understanding code whenever possible (editing supported languages)

# Local Testing and PGBouncer Information

## Running TestKube Tests Locally

### Prerequisites
1. **Kubernetes Context**: Switch to the correct context
   ```bash
   kubectl config use-context fbg-inf-dev-1
   # Alias: kcuc fbg-inf-dev-1
   ```

2. **TestKube CLI**: Install TestKube CLI following [TestKube documentation](https://docs.testkube.io/getting-started/step1-installing-cli)

3. **Secrets**: Tests use the `performance-cicd-credentials` secret in the `testkube` namespace which contains:
   - NATS credentials (nats-username, nats-password)
   - IGT credentials (igt-user, igt-password)
   - Various API client secrets and keys

### Running Tests
**CRITICAL**: Always explicitly specify the Kubernetes context to prevent accidental deployments to wrong environments.

#### TestKube CLI Setup and Execution
```bash
# 1. Set current kubectl context first (for safety)
kubectl config use-context fbg-inf-dev-1

# 2. Configure testkube to use proxy client mode with current context
testkube set context --client proxy --kubeconfig ~/.kube/config --namespace testkube

# 3. Run TestWorkflows with watch for real-time output
testkube run testworkflow k6-pgbouncer-rolling-restart-psql --watch

# Alternative method if testkube CLI has connection issues:
kubectl create -f - <<EOF
apiVersion: testworkflows.testkube.io/v1
kind: TestWorkflowExecution
metadata:
  name: pgbouncer-test-\$(date +%s)
  namespace: testkube
spec:
  testWorkflow:
    name: k6-pgbouncer-rolling-restart-psql
EOF
```

#### Legacy Test Commands (for older Test CRDs)
```bash
# Basic test execution - ALWAYS specify context
kubectl --context=fbg-inf-dev-1 testkube run test <test-name> -v TEST_ENVIRONMENT=fbg-inf-dev-1

# With secret variables - ALWAYS specify context
kubectl --context=fbg-inf-dev-1 testkube run testworkflow casino-bet-placement-v2 \
  -v TEST_ENVIRONMENT=fbg-inf-dev-1 \
  --secret-variable IGT_USER=username \
  --secret-variable IGT_PW=password

# Deployment - ALWAYS specify context
kubectl --context=fbg-inf-dev-1 apply -f tests/your-service/your-test.yaml

# General kubectl commands - ALWAYS specify context
kubectl --context=fbg-inf-dev-1 get tests -n testkube
kubectl --context=fbg-inf-dev-1 get pods -n testkube
```

#### TestKube Execution Best Practices
- **Always use proxy client mode** when working locally with TestKube CLI
- **Set kubectl context first** before configuring testkube to ensure proper cluster targeting  
- **Use --watch flag** to see real-time test output and logs
- **Verify branch targeting** in test YAML files when developing new tests (should point to feature branch)
- **TestWorkflows use Amazon Linux base image** from `public.ecr.aws/amazonlinux/amazonlinux:2`
- **SSM credentials** are automatically fetched using service account IAM roles - never hardcode them

### PGBouncer Configuration
- **Service**: `pgbouncer-ats` in `fbg-inf-dev-1` namespace on port 5432
- **Authentication**: Uses AWS IAM roles and SSM Parameter Store (not username/password)
- **Configuration**: Managed via confd containers reading from AWS SSM
- **AWS Role**: `arn:aws:iam::222019643140:role/eks-application-iam-pgbouncer-role`
- **SSM Parameters**: Environment-specific paths resolved by Flux/Kustomize:
  - `/${ENVIRONMENT_NAME}/pgbouncer-ats/db-username`
  - `/${ENVIRONMENT_NAME}/pgbouncer-ats/db-password`

### TestKube Web UI
Access tests via: https://testkube.cicd.fanatics.bet/clusters/inf-dev-1/tests

## Performance Testing Documentation
- **Main Guide**: [TestKube Deployment and Testing Guide](../docs/deployment-guide.md)
  - Complete deployment process from code to execution
  - Test vs TestWorkflow CRD differences
  - GitHub Actions integration
  - Authentication patterns (SSM, service accounts)
  - Troubleshooting and best practices
  
- **Service-Specific Guides**:
  - [PGBouncer Tests](../tests/pgbouncer/README.md) - Database connection stability testing
  - [Common Utils](../docs/commonutils.md) - Shared test utilities
  - [Test Profile Setup](../docs/testProfileSetUp.md) - Environment-specific configurations

# Local Docker Testing Requirements (pgbouncer-images project)

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

**Common Issues:**
- **Docker daemon not running**: Start Docker Desktop
- **Permission denied**: Ensure user has Docker access (`docker info`)
- **Build failures**: Use `make debug` for verbose output
- **Disk space**: Use `make clean-all` to free up space

**Build Failure Debugging:**
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

**Docker + Make Advantages:**
- ✅ **Simple and reliable** - standard Docker workflow everyone knows
- ✅ **No complex tooling** - just Docker + Make (built-in)
- ✅ **Easy debugging** - familiar Docker commands and logs
- ✅ **CI/CD compatible** - same commands work locally and in pipelines
- ✅ **Comprehensive validation** - complete pre-push checklist

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.

      
      IMPORTANT: this context may or may not be relevant to your tasks. You should not respond to this context unless it is highly relevant to your task.
- Always use the SUCCESS framework to guide your communication style