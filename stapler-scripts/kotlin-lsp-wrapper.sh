#!/bin/bash
#
# kotlin-lsp-wrapper.sh
#
# Wrapper script for OpenCode to launch Kotlin LSP.
# Checks for installation, installs if needed, sets JAVA_HOME, and launches.
#

set -e

# Function to find Java home
find_java_home() {
    # Try common Java locations
    for java_home in \
        "/usr/lib/jvm/java-21-openjdk" \
        "/usr/lib/jvm/java-17-openjdk" \
        "/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home" \
        "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home" \
        "/Library/Java/JavaVirtualMachines/openjdk-21.jdk/Contents/Home" \
        "/Library/Java/JavaVirtualMachines/openjdk-17.jdk/Contents/Home"; do
        if [ -d "$java_home" ] && [ -x "$java_home/bin/java" ]; then
            echo "$java_home"
            return 0
        fi
    done

    # Try using java_home command on macOS
    if command -v /usr/libexec/java_home &> /dev/null; then
        /usr/libexec/java_home 2>/dev/null || echo ""
        return 0
    fi

    # Fallback: check JAVA_HOME environment variable
    if [ -n "$JAVA_HOME" ] && [ -x "$JAVA_HOME/bin/java" ]; then
        echo "$JAVA_HOME"
        return 0
    fi

    # Last resort: find java in PATH and get its home
    if command -v java &> /dev/null; then
        java -XshowSettings:properties 2>&1 | grep -E "java\.home" | cut -d'=' -f2 | tr -d '[:space:]' || echo ""
        return 0
    fi

    echo ""
}

# Function to check/install kotlin-lsp
ensure_kotlin_lsp() {
    if command -v kotlin-lsp &> /dev/null; then
        return 0
    fi

    echo "Kotlin LSP not found. Attempting to install..." >&2

    # Try different installation methods
    if command -v brew &> /dev/null; then
        if brew install kotlin-lsp 2>/dev/null; then
            echo "Installed Kotlin LSP via Homebrew" >&2
            return 0
        fi
    fi

    if command -v nix-env &> /dev/null; then
        if nix-env -iA nixpkgs.kotlin-lsp 2>/dev/null; then
            echo "Installed Kotlin LSP via Nix" >&2
            return 0
        fi
    fi

    # Try to download and install standalone
    if command -v curl &> /dev/null && command -v unzip &> /dev/null; then
        local temp_dir=$(mktemp -d)
        local zip_url="https://github.com/Kotlin/kotlin-lsp/releases/download/1.3.9/kotlin-lsp-1.3.9.zip"

        if curl -L -o "$temp_dir/kotlin-lsp.zip" "$zip_url" 2>/dev/null && \
           unzip -q "$temp_dir/kotlin-lsp.zip" -d "$temp_dir" 2>/dev/null; then

            local binary_path=$(find "$temp_dir" -name "kotlin-lsp" -type f -executable 2>/dev/null | head -1)
            if [ -n "$binary_path" ]; then
                mkdir -p ~/.local/bin 2>/dev/null || true
                cp "$binary_path" ~/.local/bin/ 2>/dev/null || true
                chmod +x ~/.local/bin/kotlin-lsp 2>/dev/null || true
                export PATH="$HOME/.local/bin:$PATH"
                rm -rf "$temp_dir"
                echo "Installed Kotlin LSP standalone binary" >&2
                return 0
            fi
        fi
        rm -rf "$temp_dir"
    fi

    echo "Failed to install Kotlin LSP. Please run: ./stapler-scripts/kotlin-lsp-installer.sh" >&2
    return 1
}

# Main logic
main() {
    # Set JAVA_HOME dynamically
    JAVA_HOME=$(find_java_home)
    if [ -n "$JAVA_HOME" ]; then
        export JAVA_HOME
        export PATH="$JAVA_HOME/bin:$PATH"
    else
        echo "Warning: Could not find Java installation" >&2
    fi

    # Ensure kotlin-lsp is available
    if ! ensure_kotlin_lsp; then
        echo "Error: Kotlin LSP not available" >&2
        exit 1
    fi

    # Launch kotlin-lsp with all arguments passed through
    exec kotlin-lsp "$@"
}

main "$@"