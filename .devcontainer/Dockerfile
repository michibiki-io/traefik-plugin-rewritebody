FROM mcr.microsoft.com/devcontainers/go:1.27-trixie

RUN apt-get update \
    && apt-get install -y --no-install-recommends vim \
    && rm -rf /var/lib/apt/lists/*

USER vscode
RUN go install mvdan.cc/gofumpt@v0.12.0 \
    && go install github.com/traefik/yaegi/cmd/yaegi@v0.16.3
