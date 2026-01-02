#!/usr/bin/env bash
#
# kotlin-lsp-installer.sh
#
# Wrapper script to install Kotlin LSP server if not already present.
# Kotlin LSP provides IntelliJ-grade language server support for Kotlin files.
#
# Usage:
#   ./kotlin-lsp-installer.sh        # Install if not present
#   ./kotlin-lsp-installer.sh --force # Force reinstall
#   ./kotlin-lsp-installer.sh --check # Just check if installed
#

set -e  # Exit on any error

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

# Check if kotlin-lsp is installed
check_kotlin_lsp() {
    if command -v kotlin-lsp &> /dev/null; then
        local version=$(kotlin-lsp --version 2>/dev/null || echo "unknown version")
        log_success "Kotlin LSP is installed: $version"
        return 0
    else
        log_warning "Kotlin LSP is not installed"
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
        if [ "$version" -ge 17 ]; then
            log_success "Java $version is available (✓ meets requirement)"
            return 0
        else
            log_warning "Java $version detected, but Java 17+ is recommended"
            return 0  # Still allow installation
        fi
    else
        log_error "Java is not installed. Kotlin LSP requires Java 17+"
        echo "  Please install Java first:"
        echo "  - Ubuntu/Debian: sudo apt install openjdk-21-jdk"
        echo "  - macOS: brew install openjdk@21"
        echo "  - Arch: sudo pacman -S jdk21-openjdk"
        return 1
    fi
}

# Install kotlin-lsp
install_kotlin_lsp() {
    local install_method=""

    # Try different installation methods
    log_info "Attempting to install Kotlin LSP..."

    # Method 1: Try Homebrew (if available)
    if check_brew; then
        log_info "Trying Homebrew installation..."
        if brew tap JetBrains/utils 2>/dev/null && brew install kotlin-lsp; then
            install_method="homebrew"
        fi
    fi

    # Method 2: Try Nix (if available)
    if [ -z "$install_method" ] && command -v nix-env &> /dev/null; then
        log_info "Trying Nix installation..."
        if nix-env -iA nixpkgs.kotlin-lsp; then
            install_method="nix"
        fi
    fi

    # Method 3: Try downloading standalone binary
    if [ -z "$install_method" ]; then
        log_info "Trying standalone binary installation..."
        if install_standalone_binary; then
            install_method="standalone"
        fi
    fi

    if [ -n "$install_method" ]; then
        log_success "Kotlin LSP installed successfully via $install_method"

        # Verify installation
        if kotlin-lsp --version &> /dev/null; then
            local version=$(kotlin-lsp --version)
            log_success "Installation verified: $version"
        else
            log_error "Installation completed but kotlin-lsp command not found"
            log_info "You may need to restart your terminal or run: source ~/.zshrc"
            return 1
        fi
    else
        log_error "All installation methods failed"
        echo "  Manual installation options:"
        echo "  1. Download VSIX from: https://github.com/Kotlin/kotlin-lsp/releases"
        echo "     Extract with: unzip kotlin-lsp-*.vsix 'extension/server/*' -d /tmp/kotlin-lsp"
        echo "     Add to PATH: export PATH=\"/tmp/kotlin-lsp/extension/server:\$PATH\""
        echo "  2. Use VS Code extension (includes LSP server)"
        return 1
    fi
}

# Install standalone binary
install_standalone_binary() {
    local temp_dir=$(mktemp -d)
    local zip_url="https://github.com/Kotlin/kotlin-lsp/releases/latest/download/kotlin-lsp-0.1.0.zip"

    log_info "Downloading standalone Kotlin LSP..."

    # Try to download and extract
    if command -v curl &> /dev/null && curl -L -o "$temp_dir/kotlin-lsp.zip" "$zip_url" 2>/dev/null; then
        if command -v unzip &> /dev/null && unzip -q "$temp_dir/kotlin-lsp.zip" -d "$temp_dir"; then
            # Find the binary
            local binary_path=$(find "$temp_dir" -name "kotlin-lsp" -type f -executable 2>/dev/null | head -1)
            if [ -n "$binary_path" ]; then
                # Copy to local bin directory
                mkdir -p ~/.local/bin
                cp "$binary_path" ~/.local/bin/
                chmod +x ~/.local/bin/kotlin-lsp

                # Clean up
                rm -rf "$temp_dir"
                return 0
            fi
        fi
    fi

    # Clean up and return failure
    rm -rf "$temp_dir"
    return 1
}

# Show usage information
show_usage() {
    cat << EOF
kotlin-lsp-installer.sh

Wrapper script to install Kotlin LSP server for IntelliJ-grade Kotlin support.

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --check     Only check if Kotlin LSP is installed (no installation)
    --force     Force reinstallation even if already installed
    --help      Show this help message

EXAMPLES:
    $0                    # Install if not present
    $0 --force           # Force reinstall
    $0 --check           # Just check installation status

REQUIREMENTS:
    - Homebrew (brew)
    - Java 17+ (recommended)

After installation, Kotlin LSP will be available for:
    - .kt files (Kotlin source)
    - .kts files (Kotlin scripts)

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

    echo "🔧 Kotlin LSP Installer"
    echo "======================="
    echo

    # Check if only checking status
    if $check_only; then
        check_kotlin_lsp && exit 0 || exit 1
    fi

    # Check current installation status
    if check_kotlin_lsp && ! $force_install; then
        log_info "Kotlin LSP is already installed. Use --force to reinstall."
        exit 0
    fi

    # Check prerequisites
    log_info "Checking prerequisites..."

    if ! check_brew; then
        exit 1
    fi

    if ! check_java; then
        exit 1
    fi

    log_info "Prerequisites check complete"

    # Install Kotlin LSP
    if ! install_kotlin_lsp; then
        exit 1
    fi

    echo
    log_success "Kotlin LSP installation completed!"
    echo
    echo "🎯 Next steps:"
    echo "  1. OpenCode will automatically detect .kt/.kts files"
    echo "  2. Kotlin LSP will start when you open Kotlin files"
    echo "  3. Enjoy IntelliJ-grade Kotlin language support!"
    echo
    echo "📖 For more info: https://github.com/Kotlin/kotlin-lsp"
}

# Run main function
main "$@"