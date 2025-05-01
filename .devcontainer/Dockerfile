ARG VARIANT=3
FROM mcr.microsoft.com/vscode/devcontainers/python:${VARIANT}

RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install --no-install-recommends -y bc fontforge \
    && fontforge --version 2>&1

# Create a virtual environment and install pytest for refactoring
RUN python3 -m venv --upgrade-deps /workspace/nerd-fonts/.venv \
    && /workspace/nerd-fonts/.venv/bin/pip install --upgrade pip setuptools \
    && /workspace/nerd-fonts/.venv/bin/pip install pytest pytest-benchmark

ENV PATH="/workspace/nerd-fonts/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/workspace/nerd-fonts/.venv"
