# Base Image: Lightweight Python
FROM python:3.11-slim

# 1. System Dependencies
# - git: Required by Aider for repo management
# - curl: For health checks or downloading tools
# - procps: For 'ps' command debugging
RUN apt-get update && apt-get install -y \
    git \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 2. AI & Agent Stack
# - aider-chat: The coding agent
# - litellm: The model adapter
# - google-cloud-aiplatform: For Vertex AI
RUN pip install --no-cache-dir \
    aider-chat \
    litellm \
    google-cloud-aiplatform

# 3. Environment Setup
WORKDIR /repo

# 4. Default Entrypoint (Can be overridden)
# By default, act as the Brain (Aider)
ENTRYPOINT ["aider"]
CMD []
