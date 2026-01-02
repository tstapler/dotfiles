#!/bin/bash
#
# clojure-lsp-installer.sh
#
# Installer script for Clojure LSP server with comprehensive installation methods.
# Supports all major platforms and package managers.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ${NC}  $1"
}

log_success() {
    echo -e "${GREEN}✓${NC}  $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

log_error() {
    echo -e "${RED}✗${NC}  $1"
}

# Check if clojure-lsp is installed
check_clojure_lsp() {
    if command -v clojure-lsp &> /dev/null; then
        local version=$(clojure-lsp --version 2>/dev/null || echo "unknown version")
        log_success "Clojure LSP is installed: $version"
        return 0
    else
        log_warning "Clojure LSP is not installed"
        return 1
    fi
}

# Check if brew is available
check_brew() {
    if command -v brew &> /dev/null; then
        log_info "Homebrew is available"
        return 0
    else
        log_error "Homebrew is not installed. Please install Homebrew first:"
        echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        return 1
    fi
}

# Check Java requirements
check_java() {
    if command -v java &> /dev/null; then
        local version=$(java -version 2>&1 | head -n 1 | cut -d'"' -f2 | cut -d'.' -f1)
        if [ "$version" -ge 8 ]; then
            log_success "Java $version is available (✓ meets requirement)"
            return 0
        else
            log_warning "Java $version detected, but Java 8+ is recommended for Clojure LSP"
            return 0  # Still allow installation
        fi
    else
        log_error "Java is not installed. Clojure LSP requires Java 8+"
        echo "  Please install Java first:"
        echo "  - Ubuntu/Debian: sudo apt install openjdk-11-jdk"
        echo "  - macOS: brew install openjdk@11"
        echo "  - Arch: sudo pacman -S jdk11-openjdk"
        return 1
    fi
}

# Check Clojure requirements
check_clojure() {
    if command -v clojure &> /dev/null; then
        log_success "Clojure CLI is available"
        return 0
    elif command -v lein &> /dev/null; then
        log_success "Leiningen is available"
        return 0
    elif command -v bb &> /dev/null; then
        log_success "Babashka is available"
        return 0
    else
        log_warning "No Clojure tooling detected. Clojure LSP works best with Clojure CLI, Leiningen, or Babashka"
        return 0  # Not required for basic LSP functionality
    fi
}

# Install clojure-lsp via brew
install_via_brew() {
    log_info "Installing Clojure LSP via Homebrew..."

    # Add tap if not already added
    brew tap clojure-lsp/brew 2>/dev/null || true

    if brew install clojure-lsp-native; then
        log_success "Clojure LSP installed successfully via Homebrew"
        return 0
    else
        log_error "Homebrew installation failed"
        return 1
    fi
}

# Install via Nix
install_via_nix() {
    log_info "Installing Clojure LSP via Nix..."

    if nix-env -iA nixpkgs.clojure-lsp; then
        log_success "Clojure LSP installed successfully via Nix"
        return 0
    else
        log_error "Nix installation failed"
        return 1
    fi
}

# Install via pacman (Arch Linux)
install_via_pacman() {
    log_info "Installing Clojure LSP via pacman..."

    if pacman -S clojure-lsp-bin; then
        log_success "Clojure LSP installed successfully via pacman"
        return 0
    else
        log_error "pacman installation failed"
        return 1
    fi
}

# Install standalone binary
install_standalone() {
    log_info "Installing Clojure LSP standalone binary..."

    local temp_dir=$(mktemp -d)
    local zip_url="https://github.com/clojure-lsp/clojure-lsp/releases/latest/download/clojure-lsp-native-linux-amd64.zip"

    log_info "Downloading from: $zip_url"

    if curl -L -o "$temp_dir/clojure-lsp.zip" "$zip_url"; then
        log_info "Extracting archive..."
        if unzip -q "$temp_dir/clojure-lsp.zip" -d "$temp_dir"; then
            local binary_path=$(find "$temp_dir" -name "clojure-lsp" -type f -executable | head -1)

            if [ -n "$binary_path" ]; then
                mkdir -p ~/.local/bin
                cp "$binary_path" ~/.local/bin/
                chmod +x ~/.local/bin/clojure-lsp

                # Add to PATH for current session
                export PATH="$HOME/.local/bin:$PATH"

                rm -rf "$temp_dir"
                log_success "Clojure LSP installed successfully as standalone binary"
                return 0
            else
                log_error "Binary not found in extracted archive"
            fi
        else
            log_error "Failed to extract archive"
        fi
    else
        log_error "Failed to download archive"
    fi

    rm -rf "$temp_dir"
    return 1
}

# Show usage information
show_usage() {
    cat << EOF
clojure-lsp-installer.sh

Installer script for Clojure LSP server with comprehensive platform support.

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --check     Only check if Clojure LSP is installed (no installation)
    --force     Force reinstallation even if already installed
    --help      Show this help message

INSTALLATION METHODS (tried in order):
    1. Homebrew (macOS/Linux)
    2. Nix package manager
    3. pacman (Arch Linux)
    4. Standalone binary download

REQUIREMENTS:
    - Java 8+ (recommended 11+)
    - Optional: Clojure CLI, Leiningen, or Babashka for full functionality

AFTER INSTALLATION:
    Clojure LSP will provide IntelliJ-grade support for:
    - .clj files (Clojure)
    - .cljs files (ClojureScript)
    - .cljc files (Clojure/Common)
    - .edn files (data files)
    - .bb files (Babashka scripts)

EOF
}

# Main logic
main() {
    local force_install=false
    local check_only=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force)
                force_install=true
                shift
                ;;
            --check)
                check_only=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    echo "🟢 Clojure LSP Installer"
    echo "======================="
    echo

    # Check if only checking status
    if $check_only; then
        check_clojure_lsp && exit 0 || exit 1
    fi

    # Check current installation status
    if check_clojure_lsp && ! $force_install; then
        log_info "Clojure LSP is already installed. Use --force to reinstall."
        exit 0
    fi

    # Check prerequisites
    log_info "Checking prerequisites..."

    if ! check_java; then
        exit 1
    fi

    check_clojure  # Not required, just informational

    log_info "Prerequisites check complete"

    # Try different installation methods
    if check_brew && install_via_brew; then
        : # Success
    elif command -v nix-env &> /dev/null && install_via_nix; then
        : # Success
    elif command -v pacman &> /dev/null && install_via_pacman; then
        : # Success
    elif install_standalone; then
        : # Success
    else
        log_error "All installation methods failed!"
        echo
        echo "Manual installation options:"
        echo "1. Download from: https://github.com/clojure-lsp/clojure-lsp/releases"
        echo "2. Extract and add 'clojure-lsp' to your PATH"
        echo "3. Or use your system's package manager"
        exit 1
    fi

    echo
    log_success "Clojure LSP installation completed!"
    echo
    echo "🎯 Next steps:"
    echo "  1. OpenCode will automatically detect .clj/.cljs/.cljc/.edn files"
    echo "  2. LSP will start when you open Clojure files"
    echo "  3. Enjoy IntelliJ-grade Clojure development support!"
    echo
    echo "📖 For more info: https://clojure-lsp.io/"
}

# Run main function
main "$@"