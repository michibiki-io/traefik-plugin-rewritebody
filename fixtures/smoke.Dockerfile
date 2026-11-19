FROM traefik:v3.7.19 AS upstream-traefik
FROM traefik/whoami:v1.12.0 AS upstream-whoami

FROM debian:trixie-slim AS traefik
COPY --from=upstream-traefik /usr/local/bin/traefik /usr/local/bin/traefik
ENTRYPOINT ["/usr/local/bin/traefik"]

FROM debian:trixie-slim AS whoami
COPY --from=upstream-whoami /whoami /usr/local/bin/whoami
ENTRYPOINT ["/usr/local/bin/whoami"]
