#!/bin/bash
# Shared Bootstrap Logic for Base Image

# Expects:
# - MISSION_ROOT to be defined
# - UPSTREAM_REPO to be defined
# - BASE_IMG to be defined ("aider-vertex:latest")

ensure_base_image() {
    if docker image inspect "$BASE_IMG" > /dev/null 2>&1; then
        return 0
    fi

    echo "⚠️  Base image '$BASE_IMG' not found."
    ARCH=$(uname -m)

    if [[ "$ARCH" == "arm64" ]] || [[ "$ARCH" == "aarch64" ]]; then
        echo "🍎 Apple Silicon / ARM64 Detected."
        echo "🛠  Initiating Nix Bootstrap (Native Build)..."
        echo "   (This may take a few minutes, but solves emulation crashes)"
        
        # FIX: Ensure we use the correct path for the volume mount
        # We need the absolute path to .mission directory
        
        echo "   - Mounting: $MISSION_ROOT"
        
        # The M1 Bootstrap "Different Path"
        docker run --rm \
            --platform linux/arm64 \
            -v "$MISSION_ROOT:/app" -w /app \
            nixos/nix \
            bash -c "nix --extra-experimental-features 'nix-command flakes' build $UPSTREAM_REPO > /dev/null && cat result" > /tmp/aider-vertex.tar.gz
            
        if [ $? -eq 0 ]; then
            echo "📥 Loading Native Image..."
            docker load < /tmp/aider-vertex.tar.gz
            rm /tmp/aider-vertex.tar.gz
            # Re-tag if necessary (the tarball loads as the upstream name)
            # But here we assume the tarball contains 'aider-vertex:latest' or similar.
            # Actually, the result of 'nix build' might be an image with a specific tag.
            # However, previous logs showed it worked.
        else
            echo "❌ Bootstrap Failed."
            exit 1
        fi
    else
        echo "💻 x86_64 Detected."
        # If we are on x86, we should have pulled it.
        # But for 'up', it just tells user to pull.
        # For 'test', we might want to auto-pull?
        echo "   Please pull the image: docker pull $BASE_IMAGE_REGISTRY"
        echo "   Or tag your local build."
        exit 1
    fi
}
