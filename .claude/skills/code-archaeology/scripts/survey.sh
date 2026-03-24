#!/bin/bash
# Code Archaeology - Structural Survey Script
# Performs automated tech stack detection, file tree generation, and dependency extraction.
#
# Usage: survey.sh <project-directory> [--json]
#
# Outputs a structured overview of the codebase including:
#   - File tree (depth-limited)
#   - Tech stack detection (language, framework, build system)
#   - Dependency inventory
#   - Entry point candidates
#   - Configuration files
#   - Test presence signal
#   - Infrastructure fingerprint
#
# This script is READ-ONLY. It never executes project code, installs dependencies,
# or modifies any files.

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

PROJECT_DIR="${1:?Usage: survey.sh <project-directory> [--json]}"
OUTPUT_FORMAT="${2:-text}"
MAX_TREE_DEPTH=3
MAX_FILES_SHOWN=200

# Colors (disabled for JSON output)
if [[ "$OUTPUT_FORMAT" != "--json" ]]; then
    BOLD='\033[1m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    BOLD='' GREEN='' YELLOW='' BLUE='' NC=''
fi

# =============================================================================
# Utility Functions
# =============================================================================

section() {
    if [[ "$OUTPUT_FORMAT" != "--json" ]]; then
        echo -e "\n${BOLD}${BLUE}=== $1 ===${NC}\n"
    fi
}

found() {
    if [[ "$OUTPUT_FORMAT" != "--json" ]]; then
        echo -e "  ${GREEN}[FOUND]${NC} $1"
    fi
}

not_found() {
    if [[ "$OUTPUT_FORMAT" != "--json" ]]; then
        echo -e "  ${YELLOW}[----]${NC} $1"
    fi
}

check_file() {
    local file="$1"
    local label="$2"
    if [[ -f "$PROJECT_DIR/$file" ]]; then
        found "$label ($file)"
        return 0
    else
        return 1
    fi
}

check_glob() {
    local pattern="$1"
    local label="$2"
    local matches
    matches=$(find "$PROJECT_DIR" -maxdepth 4 -name "$pattern" -type f 2>/dev/null | head -5)
    if [[ -n "$matches" ]]; then
        local count
        count=$(echo "$matches" | wc -l | tr -d ' ')
        found "$label ($count files matching $pattern)"
        return 0
    else
        return 1
    fi
}

# =============================================================================
# Validation
# =============================================================================

if [[ ! -d "$PROJECT_DIR" ]]; then
    echo "ERROR: Directory not found: $PROJECT_DIR" >&2
    exit 1
fi

cd "$PROJECT_DIR"

echo -e "${BOLD}Code Archaeology - Structural Survey${NC}"
echo "Project: $PROJECT_DIR"
echo "Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"

# =============================================================================
# 1. File Tree Overview
# =============================================================================

section "1. File Tree Overview"

# Total file count
total_files=$(find . -type f -not -path './.git/*' -not -path './node_modules/*' \
    -not -path './vendor/*' -not -path './.venv/*' -not -path './venv/*' \
    -not -path './target/*' -not -path './build/*' -not -path './__pycache__/*' \
    -not -path './.next/*' -not -path './dist/*' 2>/dev/null | wc -l | tr -d ' ')
echo "Total files (excluding build/vendor): $total_files"
echo ""

# Depth-limited tree (prefer tree command if available)
if command -v tree &>/dev/null; then
    tree -L "$MAX_TREE_DEPTH" -I 'node_modules|vendor|.venv|venv|target|build|__pycache__|.next|dist|.git' \
        --dirsfirst --filelimit 20 2>/dev/null | head -"$MAX_FILES_SHOWN"
else
    find . -maxdepth "$MAX_TREE_DEPTH" -not -path './.git/*' -not -path './node_modules/*' \
        -not -path './vendor/*' -not -path './.venv/*' -not -path './target/*' \
        -not -path './build/*' 2>/dev/null | sort | head -"$MAX_FILES_SHOWN"
fi

# File extension distribution
section "1b. File Extension Distribution"
find . -type f -not -path './.git/*' -not -path './node_modules/*' \
    -not -path './vendor/*' -not -path './.venv/*' -not -path './venv/*' \
    -not -path './target/*' -not -path './build/*' -not -path './__pycache__/*' \
    -not -path './.next/*' -not -path './dist/*' 2>/dev/null | \
    sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20

# =============================================================================
# 2. Tech Stack Detection
# =============================================================================

section "2. Tech Stack Detection"

DETECTED_LANGS=()
DETECTED_FRAMEWORKS=()
DETECTED_BUILD=()

# --- Languages ---
echo -e "${BOLD}Languages:${NC}"

if check_file "package.json" "JavaScript/TypeScript"; then
    DETECTED_LANGS+=("JavaScript/TypeScript")
    if [[ -f "tsconfig.json" ]]; then
        found "TypeScript confirmed (tsconfig.json)"
        DETECTED_LANGS+=("TypeScript")
    fi
fi

if check_file "pom.xml" "Java (Maven)"; then
    DETECTED_LANGS+=("Java")
    DETECTED_BUILD+=("Maven")
fi

if check_file "build.gradle" "Java/Kotlin (Gradle)" || check_file "build.gradle.kts" "Kotlin (Gradle KTS)"; then
    DETECTED_LANGS+=("Java/Kotlin")
    DETECTED_BUILD+=("Gradle")
fi

if check_file "go.mod" "Go"; then
    DETECTED_LANGS+=("Go")
fi

if check_file "Cargo.toml" "Rust"; then
    DETECTED_LANGS+=("Rust")
    DETECTED_BUILD+=("Cargo")
fi

if check_file "requirements.txt" "Python (requirements.txt)" || \
   check_file "pyproject.toml" "Python (pyproject.toml)" || \
   check_file "setup.py" "Python (setup.py)"; then
    DETECTED_LANGS+=("Python")
fi

if check_file "Gemfile" "Ruby"; then
    DETECTED_LANGS+=("Ruby")
fi

if check_file "mix.exs" "Elixir"; then
    DETECTED_LANGS+=("Elixir")
fi

check_glob "*.csproj" "C#/.NET" && DETECTED_LANGS+=(".NET")
check_glob "*.sln" "C#/.NET Solution" || true

if check_file "composer.json" "PHP"; then
    DETECTED_LANGS+=("PHP")
fi

# --- Frameworks ---
echo ""
echo -e "${BOLD}Frameworks:${NC}"

# Java/Kotlin frameworks
if grep -rq "@SpringBootApplication" --include="*.java" --include="*.kt" . 2>/dev/null; then
    found "Spring Boot"
    DETECTED_FRAMEWORKS+=("Spring Boot")
fi

# Python frameworks
if [[ -f "requirements.txt" ]]; then
    grep -qi "django" requirements.txt 2>/dev/null && found "Django" && DETECTED_FRAMEWORKS+=("Django")
    grep -qi "flask" requirements.txt 2>/dev/null && found "Flask" && DETECTED_FRAMEWORKS+=("Flask")
    grep -qi "fastapi" requirements.txt 2>/dev/null && found "FastAPI" && DETECTED_FRAMEWORKS+=("FastAPI")
fi
if [[ -f "pyproject.toml" ]]; then
    grep -qi "django" pyproject.toml 2>/dev/null && found "Django" && DETECTED_FRAMEWORKS+=("Django")
    grep -qi "fastapi" pyproject.toml 2>/dev/null && found "FastAPI" && DETECTED_FRAMEWORKS+=("FastAPI")
fi

# Node frameworks
if [[ -f "package.json" ]]; then
    grep -q '"express"' package.json 2>/dev/null && found "Express.js" && DETECTED_FRAMEWORKS+=("Express.js")
    grep -q '"next"' package.json 2>/dev/null && found "Next.js" && DETECTED_FRAMEWORKS+=("Next.js")
    grep -q '"nuxt"' package.json 2>/dev/null && found "Nuxt.js" && DETECTED_FRAMEWORKS+=("Nuxt.js")
    grep -q '"@nestjs/core"' package.json 2>/dev/null && found "NestJS" && DETECTED_FRAMEWORKS+=("NestJS")
    grep -q '"react"' package.json 2>/dev/null && found "React" && DETECTED_FRAMEWORKS+=("React")
    grep -q '"vue"' package.json 2>/dev/null && found "Vue.js" && DETECTED_FRAMEWORKS+=("Vue.js")
    grep -q '"svelte"' package.json 2>/dev/null && found "Svelte" && DETECTED_FRAMEWORKS+=("Svelte")
    grep -q '"hono"' package.json 2>/dev/null && found "Hono" && DETECTED_FRAMEWORKS+=("Hono")
fi

# Go frameworks
if [[ -f "go.mod" ]]; then
    grep -q "gin-gonic/gin" go.mod 2>/dev/null && found "Gin (Go)" && DETECTED_FRAMEWORKS+=("Gin")
    grep -q "labstack/echo" go.mod 2>/dev/null && found "Echo (Go)" && DETECTED_FRAMEWORKS+=("Echo")
    grep -q "go-chi/chi" go.mod 2>/dev/null && found "Chi (Go)" && DETECTED_FRAMEWORKS+=("Chi")
    grep -q "gofiber/fiber" go.mod 2>/dev/null && found "Fiber (Go)" && DETECTED_FRAMEWORKS+=("Fiber")
fi

# Rust frameworks
if [[ -f "Cargo.toml" ]]; then
    grep -q "actix-web" Cargo.toml 2>/dev/null && found "Actix Web (Rust)" && DETECTED_FRAMEWORKS+=("Actix")
    grep -q "axum" Cargo.toml 2>/dev/null && found "Axum (Rust)" && DETECTED_FRAMEWORKS+=("Axum")
    grep -q "rocket" Cargo.toml 2>/dev/null && found "Rocket (Rust)" && DETECTED_FRAMEWORKS+=("Rocket")
fi

# Ruby frameworks
if [[ -f "Gemfile" ]]; then
    grep -q "rails" Gemfile 2>/dev/null && found "Ruby on Rails" && DETECTED_FRAMEWORKS+=("Rails")
    grep -q "sinatra" Gemfile 2>/dev/null && found "Sinatra" && DETECTED_FRAMEWORKS+=("Sinatra")
fi

# PHP frameworks
if [[ -f "composer.json" ]]; then
    grep -q "laravel" composer.json 2>/dev/null && found "Laravel" && DETECTED_FRAMEWORKS+=("Laravel")
    grep -q "symfony" composer.json 2>/dev/null && found "Symfony" && DETECTED_FRAMEWORKS+=("Symfony")
fi

# =============================================================================
# 3. Infrastructure Fingerprint
# =============================================================================

section "3. Infrastructure"

echo -e "${BOLD}Containerization:${NC}"
check_file "Dockerfile" "Dockerfile" || true
check_file "docker-compose.yml" "Docker Compose" || check_file "docker-compose.yaml" "Docker Compose" || check_file "compose.yml" "Docker Compose" || true

echo ""
echo -e "${BOLD}Orchestration:${NC}"
check_glob "*.tf" "Terraform" || true
check_file "Pulumi.yaml" "Pulumi" || true
check_file "serverless.yml" "Serverless Framework" || check_file "serverless.yaml" "Serverless Framework" || true
check_file "cdk.json" "AWS CDK" || true
[[ -d "k8s" ]] || [[ -d "kubernetes" ]] && found "Kubernetes manifests" || true
[[ -d "helm" ]] || check_file "Chart.yaml" "Helm Chart" || true

echo ""
echo -e "${BOLD}CI/CD:${NC}"
[[ -d ".github/workflows" ]] && found "GitHub Actions (.github/workflows/)" || true
check_file ".gitlab-ci.yml" "GitLab CI" || true
check_file "Jenkinsfile" "Jenkins" || true
check_file ".circleci/config.yml" "CircleCI" || true
check_file "bitbucket-pipelines.yml" "Bitbucket Pipelines" || true
check_file ".travis.yml" "Travis CI" || true

echo ""
echo -e "${BOLD}Databases (from dependencies/config):${NC}"
# Check for database references in common config files
for f in docker-compose.yml docker-compose.yaml compose.yml; do
    if [[ -f "$f" ]]; then
        grep -qi "postgres" "$f" 2>/dev/null && found "PostgreSQL (in $f)"
        grep -qi "mysql\|mariadb" "$f" 2>/dev/null && found "MySQL/MariaDB (in $f)"
        grep -qi "mongo" "$f" 2>/dev/null && found "MongoDB (in $f)"
        grep -qi "redis" "$f" 2>/dev/null && found "Redis (in $f)"
        grep -qi "kafka" "$f" 2>/dev/null && found "Kafka (in $f)"
        grep -qi "rabbit" "$f" 2>/dev/null && found "RabbitMQ (in $f)"
        grep -qi "elasticsearch\|opensearch" "$f" 2>/dev/null && found "Elasticsearch/OpenSearch (in $f)"
    fi
done

# =============================================================================
# 4. Entry Points
# =============================================================================

section "4. Entry Point Candidates"

# Main functions
echo -e "${BOLD}Main/bootstrap files:${NC}"
find . -maxdepth 5 -type f \( \
    -name "main.go" -o -name "main.py" -o -name "main.rs" -o \
    -name "app.py" -o -name "app.js" -o -name "app.ts" -o \
    -name "server.py" -o -name "server.js" -o -name "server.ts" -o \
    -name "index.js" -o -name "index.ts" -o \
    -name "manage.py" -o -name "wsgi.py" -o -name "asgi.py" -o \
    -name "Program.cs" -o -name "Startup.cs" \
    \) -not -path '*/node_modules/*' -not -path '*/vendor/*' \
    -not -path '*/.venv/*' -not -path '*/dist/*' -not -path '*/build/*' \
    2>/dev/null | sort

# Java main classes
if [[ ${#DETECTED_LANGS[@]} -gt 0 ]] && printf '%s\n' "${DETECTED_LANGS[@]}" | grep -q "Java"; then
    echo ""
    echo -e "${BOLD}Java main classes:${NC}"
    grep -rl "public static void main" --include="*.java" . 2>/dev/null | head -10 || true
fi

# cmd/ directory (Go convention)
if [[ -d "cmd" ]]; then
    echo ""
    echo -e "${BOLD}Go cmd/ directory:${NC}"
    find cmd -maxdepth 2 -name "main.go" -type f 2>/dev/null || true
fi

# =============================================================================
# 5. Configuration Files
# =============================================================================

section "5. Configuration Files"

echo -e "${BOLD}Application config:${NC}"
for f in \
    ".env.example" ".env.sample" ".env.template" \
    "config.yml" "config.yaml" "config.json" "config.toml" \
    "application.yml" "application.yaml" "application.properties" \
    "appsettings.json" "appsettings.Development.json" \
    ".eslintrc*" ".prettierrc*" "tsconfig.json" \
    "jest.config.*" "vitest.config.*" "vite.config.*" "webpack.config.*"; do
    [[ -f "$f" ]] && found "$f"
done 2>/dev/null || true

# Deeper config search
find . -maxdepth 3 -type d -name "config" -not -path '*/node_modules/*' 2>/dev/null | while read -r dir; do
    found "Config directory: $dir/"
done

# =============================================================================
# 6. Test Presence
# =============================================================================

section "6. Test Coverage Signal"

test_dirs=0
test_files=0

for pattern in "test" "tests" "__tests__" "spec" "specs" "test_*" "*_test"; do
    count=$(find . -maxdepth 4 -type d -name "$pattern" -not -path '*/node_modules/*' \
        -not -path '*/vendor/*' 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$count" -gt 0 ]]; then
        found "Test directory pattern '$pattern': $count directories"
        test_dirs=$((test_dirs + count))
    fi
done

# Count test files
test_file_count=$(find . -type f \( \
    -name "*_test.go" -o -name "*_test.py" -o -name "test_*.py" -o \
    -name "*.test.js" -o -name "*.test.ts" -o -name "*.test.tsx" -o \
    -name "*.spec.js" -o -name "*.spec.ts" -o -name "*.spec.tsx" -o \
    -name "*Test.java" -o -name "*Tests.java" -o -name "*Spec.java" -o \
    -name "*_test.rs" -o -name "*_spec.rb" \
    \) -not -path '*/node_modules/*' -not -path '*/vendor/*' 2>/dev/null | wc -l | tr -d ' ')

echo ""
echo "Test directories found: $test_dirs"
echo "Test files found: $test_file_count"

if [[ "$test_file_count" -eq 0 ]]; then
    echo -e "${YELLOW}WARNING: No test files detected${NC}"
fi

# =============================================================================
# 7. Dependency Summary
# =============================================================================

section "7. Dependency Summary"

# package.json
if [[ -f "package.json" ]]; then
    echo -e "${BOLD}Node.js dependencies (package.json):${NC}"
    deps=$(jq -r '.dependencies // {} | keys[]' package.json 2>/dev/null | wc -l | tr -d ' ')
    dev_deps=$(jq -r '.devDependencies // {} | keys[]' package.json 2>/dev/null | wc -l | tr -d ' ')
    echo "  Runtime: $deps | Dev: $dev_deps"
    echo "  Top runtime deps:"
    jq -r '.dependencies // {} | keys[]' package.json 2>/dev/null | head -15 | sed 's/^/    /'
fi

# go.mod
if [[ -f "go.mod" ]]; then
    echo -e "${BOLD}Go dependencies (go.mod):${NC}"
    deps=$(grep -c "^\t" go.mod 2>/dev/null || echo "0")
    echo "  Direct dependencies: $deps"
    echo "  Top deps:"
    grep "^\t" go.mod 2>/dev/null | head -15 | sed 's/^\t/    /'
fi

# Cargo.toml
if [[ -f "Cargo.toml" ]]; then
    echo -e "${BOLD}Rust dependencies (Cargo.toml):${NC}"
    deps=$(grep -c '^\w.*=' Cargo.toml 2>/dev/null || echo "0")
    echo "  Dependencies: ~$deps entries"
    echo "  [dependencies] section:"
    sed -n '/\[dependencies\]/,/\[/p' Cargo.toml 2>/dev/null | grep -v '^\[' | head -15 | sed 's/^/    /'
fi

# requirements.txt
if [[ -f "requirements.txt" ]]; then
    echo -e "${BOLD}Python dependencies (requirements.txt):${NC}"
    deps=$(grep -cv '^\s*#\|^\s*$' requirements.txt 2>/dev/null || echo "0")
    echo "  Dependencies: $deps"
    echo "  Top deps:"
    grep -v '^\s*#\|^\s*$' requirements.txt 2>/dev/null | head -15 | sed 's/^/    /'
fi

# pyproject.toml
if [[ -f "pyproject.toml" ]]; then
    echo -e "${BOLD}Python dependencies (pyproject.toml):${NC}"
    sed -n '/\[project\]/,/\[/p' pyproject.toml 2>/dev/null | grep -v '^\[' | head -20 | sed 's/^/    /'
fi

# pom.xml (just count, don't parse XML deeply)
if [[ -f "pom.xml" ]]; then
    echo -e "${BOLD}Maven dependencies (pom.xml):${NC}"
    deps=$(grep -c "<dependency>" pom.xml 2>/dev/null || echo "0")
    echo "  Dependencies: $deps"
fi

# build.gradle
if [[ -f "build.gradle" ]] || [[ -f "build.gradle.kts" ]]; then
    local_gradle=$(ls build.gradle build.gradle.kts 2>/dev/null | head -1)
    echo -e "${BOLD}Gradle dependencies ($local_gradle):${NC}"
    deps=$(grep -c "implementation\|api\|compile" "$local_gradle" 2>/dev/null || echo "0")
    echo "  Dependencies: ~$deps"
    echo "  Implementation deps:"
    grep "implementation" "$local_gradle" 2>/dev/null | head -15 | sed 's/^/    /'
fi

# Gemfile
if [[ -f "Gemfile" ]]; then
    echo -e "${BOLD}Ruby dependencies (Gemfile):${NC}"
    deps=$(grep -c "^gem " Gemfile 2>/dev/null || echo "0")
    echo "  Gems: $deps"
    echo "  Top gems:"
    grep "^gem " Gemfile 2>/dev/null | head -15 | sed 's/^/    /'
fi

# =============================================================================
# 8. Monorepo Detection
# =============================================================================

section "8. Monorepo Detection"

is_monorepo=false

# Node workspaces
if [[ -f "package.json" ]] && jq -e '.workspaces' package.json &>/dev/null; then
    found "Node.js workspaces detected"
    jq -r '.workspaces[]? // .workspaces.packages[]?' package.json 2>/dev/null | sed 's/^/    /'
    is_monorepo=true
fi

# Lerna
if check_file "lerna.json" "Lerna monorepo"; then is_monorepo=true; fi
if check_file "nx.json" "Nx monorepo"; then is_monorepo=true; fi
if check_file "turbo.json" "Turborepo"; then is_monorepo=true; fi

# Gradle multi-project
for f in settings.gradle settings.gradle.kts; do
    if [[ -f "$f" ]] && grep -q "include" "$f" 2>/dev/null; then
        found "Gradle multi-project ($f)"
        grep "include" "$f" 2>/dev/null | head -10 | sed 's/^/    /'
        is_monorepo=true
    fi
done

# Maven multi-module
if [[ -f "pom.xml" ]] && grep -q "<modules>" pom.xml 2>/dev/null; then
    found "Maven multi-module project"
    sed -n '/<modules>/,/<\/modules>/p' pom.xml 2>/dev/null | grep "<module>" | sed 's/^/    /'
    is_monorepo=true
fi

# Go workspace
if check_file "go.work" "Go workspace"; then
    cat go.work 2>/dev/null | grep "use" | sed 's/^/    /'
    is_monorepo=true
fi

# Rust workspace
if [[ -f "Cargo.toml" ]] && grep -q "\[workspace\]" Cargo.toml 2>/dev/null; then
    found "Rust workspace (Cargo.toml)"
    sed -n '/\[workspace\]/,/\[/p' Cargo.toml 2>/dev/null | grep "members\|exclude" | head -5 | sed 's/^/    /'
    is_monorepo=true
fi

if [[ "$is_monorepo" == "false" ]]; then
    echo "  No monorepo structure detected (single project)"
fi

# =============================================================================
# 9. README and Documentation
# =============================================================================

section "9. Documentation"

for f in README.md README.rst README.txt README readme.md CONTRIBUTING.md \
         CHANGELOG.md CHANGES.md docs/README.md doc/README.md; do
    [[ -f "$f" ]] && found "$f"
done 2>/dev/null || true

# Docs directories
for d in docs doc documentation wiki; do
    if [[ -d "$d" ]]; then
        doc_count=$(find "$d" -type f 2>/dev/null | wc -l | tr -d ' ')
        found "Documentation directory: $d/ ($doc_count files)"
    fi
done

# OpenAPI / Swagger
check_glob "openapi.*" "OpenAPI spec" || true
check_glob "swagger.*" "Swagger spec" || true

# =============================================================================
# Summary
# =============================================================================

section "SURVEY COMPLETE"

echo "Languages detected: ${DETECTED_LANGS[*]:-none}"
echo "Frameworks detected: ${DETECTED_FRAMEWORKS[*]:-none}"
echo "Build systems: ${DETECTED_BUILD[*]:-none}"
echo "Total source files: $total_files"
echo "Test files: $test_file_count"
echo "Monorepo: $is_monorepo"
echo ""
echo "Next steps:"
echo "  1. Read README.md for project intent"
echo "  2. Examine entry points listed above"
echo "  3. Trace domain model from entity/model classes"
echo "  4. Map API contracts from controllers/routes"
echo "  5. Load reference.md for detailed reverse engineering patterns"
