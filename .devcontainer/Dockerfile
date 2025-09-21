# Development container for Temporal Platform
FROM mcr.microsoft.com/vscode/devcontainers/python:3.11

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    postgresql-client \
    vim \
    htop \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Install Helm
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install Temporal CLI
RUN curl -sSf https://temporal.download/cli.sh | sh

# Install Poetry
RUN pip install poetry

# Configure Poetry
RUN poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project true

# Set working directory
WORKDIR /workspace

# Create vscode user
RUN useradd -m -s /bin/bash vscode \
    && usermod -aG sudo vscode \
    && echo "vscode ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER vscode
