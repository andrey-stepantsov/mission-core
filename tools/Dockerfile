# Base Image: The Nix-based Aider env
FROM aider-vertex:latest


WORKDIR /mission

# 1. Copy Requirements
COPY requirements.txt /mission/requirements.txt

# 2. Create Virtual Environment & Install Dependencies
# We use the system python (from Nix) to create a venv.
# This avoids polluting the Nix store/system paths.
# --system-site-packages: Critical to inherit Nix-installed libs (litellm, etc)
# --system-site-packages: Critical to inherit Nix-installed libs (litellm, etc)
# RUN python3 -m venv --system-site-packages /mission/.venv && \
#    /mission/.venv/bin/pip install --no-cache-dir -r /mission/requirements.txt
RUN python3 -m venv --system-site-packages /mission/.venv

# 3. Enforce Venv PATH
# This ensures that when 'python3' is called, it's the venv version.
ENV PATH="/mission/.venv/bin:$PATH"
# We also append site-packages just in case, though PATH usually suffices.
ENV PYTHONPATH="/mission/.venv/lib/python3.11/site-packages:$PYTHONPATH"

# 4. Entrypoint
# We inherit the entrypoint from aider-vertex, which is likely 'aider-vertex' or a shell.
# But we made sure our new python libs are in the path.
