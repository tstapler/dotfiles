#!/data/data/com.termux/files/usr/bin/bash
#
# Setup ripgrep for Claude Code on Termux/Android
# Run this script whenever Claude Code updates to restore ripgrep symlinks
#
# Usage: ./setup-claude-code-ripgrep.sh

set -e

echo "=== Setting up ripgrep for Claude Code ==="

# Check if ripgrep is installed, install if not
if ! command -v rg &> /dev/null; then
    echo "📦 Installing ripgrep..."
    pkg install -y ripgrep
else
    echo "✓ ripgrep is already installed"
fi

# Get the path to ripgrep
RG_PATH=$(which rg)
echo "✓ Found ripgrep at: $RG_PATH"

# Define target directories
TARGETS=(
    "$HOME/.local/lib/node_modules/@anthropic-ai/claude-code/vendor/ripgrep/arm64-android"
    "/data/data/com.termux/files/usr/lib/node_modules/@anthropic-ai/claude-code/vendor/ripgrep/arm64-android"
)

# Create symlinks in each target directory
for TARGET_DIR in "${TARGETS[@]}"; do
    echo ""
    echo "Setting up: $TARGET_DIR"

    # Create directory if it doesn't exist
    if [ ! -d "$TARGET_DIR" ]; then
        echo "  📁 Creating directory..."
        mkdir -p "$TARGET_DIR"
    else
        echo "  ✓ Directory exists"
    fi

    # Create or update symlink
    SYMLINK="$TARGET_DIR/rg"
    if [ -L "$SYMLINK" ]; then
        # Symlink exists, check if it's correct
        CURRENT_TARGET=$(readlink "$SYMLINK")
        if [ "$CURRENT_TARGET" = "$RG_PATH" ]; then
            echo "  ✓ Symlink already correct"
        else
            echo "  🔄 Updating symlink (was pointing to $CURRENT_TARGET)"
            ln -sf "$RG_PATH" "$SYMLINK"
            echo "  ✓ Symlink updated"
        fi
    elif [ -e "$SYMLINK" ]; then
        # File exists but is not a symlink
        echo "  ⚠️  Warning: $SYMLINK exists but is not a symlink"
        echo "     Backing up and replacing..."
        mv "$SYMLINK" "$SYMLINK.backup"
        ln -sf "$RG_PATH" "$SYMLINK"
        echo "  ✓ Symlink created (old file backed up)"
    else
        # Symlink doesn't exist, create it
        echo "  🔗 Creating symlink..."
        ln -sf "$RG_PATH" "$SYMLINK"
        echo "  ✓ Symlink created"
    fi

    # Verify the symlink works
    if [ -x "$SYMLINK" ]; then
        echo "  ✓ Symlink is executable"
    else
        echo "  ⚠️  Warning: Symlink exists but is not executable"
    fi
done

echo ""
echo "=== Setup complete! ==="
echo "Claude Code should now be able to use ripgrep for searching."
