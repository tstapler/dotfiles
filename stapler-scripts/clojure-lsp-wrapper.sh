#!/bin/bash
#
# clojure-lsp-wrapper.sh
#
# Advanced wrapper for Clojure LSP with comprehensive project detection
# Supports all Clojure project types: Leiningen, CLI, Babashka, Boot, Shadow-CLJS, etc.
#

set -e

# Function to detect project type and return appropriate classpath command
detect_project_type() {
    local project_dir="$1"

    # Check for various project files in order of preference
    if [ -f "$project_dir/project.clj" ]; then
        echo "lein classpath"
    elif [ -f "$project_dir/deps.edn" ]; then
        echo "clojure -Spath"
    elif [ -f "$project_dir/bb.edn" ]; then
        echo "bb print-deps"
    elif [ -f "$project_dir/build.boot" ]; then
        echo "boot classpath"
    elif [ -f "$project_dir/shadow-cljs.edn" ]; then
        # For Shadow-CLJS, use Clojure CLI if deps.edn exists, otherwise Leiningen
        if [ -f "$project_dir/deps.edn" ]; then
            echo "clojure -Spath"
        elif [ -f "$project_dir/project.clj" ]; then
            echo "lein classpath"
        else
            echo "clojure -Spath"  # Default fallback
        fi
    else
        # No project file found - generic Clojure
        echo ""
    fi
}

# Function to find project root
find_project_root() {
    local current_dir="$1"
    local original_dir="$current_dir"

    # Walk up directory tree looking for project files
    while [ "$current_dir" != "/" ]; do
        if [ -f "$current_dir/project.clj" ] || \
           [ -f "$current_dir/deps.edn" ] || \
           [ -f "$current_dir/bb.edn" ] || \
           [ -f "$current_dir/build.boot" ] || \
           [ -f "$current_dir/shadow-cljs.edn" ]; then
            echo "$current_dir"
            return 0
        fi
        current_dir=$(dirname "$current_dir")
    done

    # No project root found, return original directory
    echo "$original_dir"
}

# Function to check/install clojure-lsp
ensure_clojure_lsp() {
    if command -v clojure-lsp &> /dev/null; then
        return 0
    fi

    echo "clojure-lsp not found. Attempting to install..." >&2

    # Try different installation methods
    if command -v brew &> /dev/null; then
        if brew tap clojure-lsp/brew && brew install clojure-lsp-native; then
            echo "Installed clojure-lsp via Homebrew" >&2
            return 0
        fi
    fi

    if command -v nix-env &> /dev/null; then
        if nix-env -iA nixpkgs.clojure-lsp; then
            echo "Installed clojure-lsp via Nix" >&2
            return 0
        fi
    fi

    if command -v pacman &> /dev/null; then
        if pacman -S clojure-lsp-bin; then
            echo "Installed clojure-lsp via pacman" >&2
            return 0
        fi
    fi

    # Try downloading standalone binary
    if command -v curl &> /dev/null && command -v unzip &> /dev/null; then
        local temp_dir=$(mktemp -d)
        local zip_url="https://github.com/clojure-lsp/clojure-lsp/releases/latest/download/clojure-lsp-native-linux-amd64.zip"

        if curl -L -o "$temp_dir/clojure-lsp.zip" "$zip_url" 2>/dev/null && \
           unzip -q "$temp_dir/clojure-lsp.zip" -d "$temp_dir" 2>/dev/null; then

            local binary_path=$(find "$temp_dir" -name "clojure-lsp" -type f -executable 2>/dev/null | head -1)
            if [ -n "$binary_path" ]; then
                mkdir -p ~/.local/bin 2>/dev/null || true
                cp "$binary_path" ~/.local/bin/ 2>/dev/null || true
                chmod +x ~/.local/bin/clojure-lsp 2>/dev/null || true
                export PATH="$HOME/.local/bin:$PATH"
                rm -rf "$temp_dir"
                echo "Installed clojure-lsp standalone binary" >&2
                return 0
            fi
        fi
        rm -rf "$temp_dir"
    fi

    echo "Failed to install clojure-lsp. Please run: ./stapler-scripts/clojure-lsp-installer.sh" >&2
    return 1
}

# Main logic
main() {
    # Get the project root directory
    local project_root=$(find_project_root "$(pwd)")

    # Ensure clojure-lsp is available
    if ! ensure_clojure_lsp; then
        echo "Error: clojure-lsp not available" >&2
        exit 1
    fi

    # Launch clojure-lsp with project root awareness
    # clojure-lsp will automatically detect project type and classpath
    cd "$project_root"
    exec clojure-lsp "$@"
}

main "$@"