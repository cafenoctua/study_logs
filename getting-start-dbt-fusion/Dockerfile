FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# Install Tools
RUN apt upgrade && apt update
RUN apt install -y \
    build-essential \
    git \
    jq \
    make

# Install tools and packages
RUN apt install -y --no-install-recommends \
  build-essential \
  curl \
  git \
  jq \
  vim \
  gnupg \
  lsb-release
  
# Clean up
RUN apt clean && rm -rf /var/lib/apt/lists/*

COPY .bashrc /root/
