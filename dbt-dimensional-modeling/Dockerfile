FROM python:3.12-slim-bookworm as dbt-dev
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
  lsb-release \
  openssh-client \
  ca-certificates

# Add Google Cloud SDK repogitory and import GPG key
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
  && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg

# Install gcloud command
RUN apt update \
  && apt install -y --fix-missing \
  google-cloud-sdk \
  google-cloud-cli

# Install python package management
RUN curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.8.4 python3 -
ENV PATH="/root/.local/bin:$PATH"


# Clean up
RUN apt clean && rm -rf /var/lib/apt/lists/*

# Create User
# Define args
# ARG uid=1100
# ARG gid=1100
# ARG username=root
# RUN addgroup --gid $gid ${username} && \
#   adduser --uid ${uid} --gid ${gid} --disabled-password --gecos "" ${username} && \
#   echo 'nonroot ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers

COPY .bashrc /root/