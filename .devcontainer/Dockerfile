FROM mcr.microsoft.com/devcontainers/python:1-3.11

# Install Node.js 20
RUN apt-get update && apt-get install -y curl &&     curl -fsSL https://deb.nodesource.com/setup_20.x | bash - &&     apt-get install -y nodejs &&     rm -rf /var/lib/apt/lists/*

# Install common dependencies
RUN apt-get update && apt-get install -y --no-install-recommends     gcc     curl     && rm -rf /var/lib/apt/lists/*

# Install pip dependencies (optional here, postCreateCommand handles it usually)
# RUN pip install --no-cache-dir -e .[dev] 
