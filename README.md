# Response Body Rewrite Plugin

This is a fork of [packruler](https://github.com/packruler)'s [rewrite-body](https://github.com/packruler/rewrite-body)
which is a fork of [Traefik](https://github.com/traefik)'s [plugin-rewritebody](https://github.com/traefik/plugin-rewritebody)

### Process For Handling Body Content

#### Body Content Requirements

* The target content must be able to be parsed as texts.
* The header must have `Content-Encoding` header that is supported by this plugin
  * The original plugin supported `Content-Encoding` of `identity` or empty
  * This plugin adds support for `gzip`, `deflate`, `brotli` encoding

#### Processing Paths

* If the `Content-Encoding` is empty or `identity` it is handled in mostly the same manner as the original plugin.

* If the `Content-Encoding` is `gzip`, `deflate` or `br` then it falls in following path:
  * The body content is decompressed
  * The resulting content is run through the `regex` process created by the original plugin
  * The processed content is then compressed with the same library and returned

**Note:** If either of conditions configured fails, then the body will be passed as is with no further processing.

## Configuration

### Static

Once a release is listed in the [Traefik Plugin Catalog](https://plugins.traefik.io/),
you can load it by version. Use the tag of the release you want to install.

```yaml
experimental:
  plugins:
    rewrite-body:
      moduleName: github.com/michibiki-io/traefik-plugin-rewritebody
      version: v0.1.0
```

You can also load the tagged source as a local plugin. Download a source archive from
[GitHub Releases](https://github.com/michibiki-io/traefik-plugin-rewritebody/releases)
and extract it, including `vendor/`, into
`./plugins-local/src/github.com/michibiki-io/traefik-plugin-rewritebody/`
relative to Traefik's working directory. For a container deployment, mount
that directory at the corresponding path inside the Traefik container.

```yaml
experimental:
  localPlugins:
    rewrite-body:
      moduleName: github.com/michibiki-io/traefik-plugin-rewritebody
```

Restart Traefik after installing or upgrading the source. Traefik reads the
plugin with Yaegi at startup.

### Dynamic

To configure the `Rewrite Body` plugin you should create a [middleware](https://docs.traefik.io/middlewares/overview/) in 
your dynamic configuration as explained [here](https://docs.traefik.io/middlewares/overview/). The following example creates
and uses the `rewrite-body` middleware plugin to replace all foo occurrences by bar in the HTTP response body.

If you want to apply some limits on the response body, you can chain this middleware plugin with the [Buffering middleware](https://docs.traefik.io/middlewares/buffering/) from Traefik.

```yaml
http:
  routers:
    my-router:
      rule: "Host(`example.com`)"
      middlewares: 
        - "rewrite-foo"
      service: "my-service"

  middlewares:
    rewrite-foo:
      plugin:
        rewrite-body:
          # Keep Last-Modified header returned by the HTTP service.
          # By default, the Last-Modified header is removed.
          lastModified: true

          # Rewrites all "foo" occurences by "bar"
          rewrites:
            - regex: "foo"
              replacement: "bar"

          # logLevel is optional, defaults to Info level.
          # Available logLevels: (Trace: -2, Debug: -1, Info: 0, Warning: 1, Error: 2)
          logLevel: 0

          # monitoring is optional, defaults to below configuration
          # monitoring configuration limits the HTTP queries that are checked for regex replacement.
          monitoring:
            # methods is a string list. Options are standard HTTP Methods. Entries MUST be ALL CAPS
            # For a list of options: https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods
            methods:
              - GET
            # types is a string list. Options are HTTP Content Types. Entries should match standard formatting
            # For a list of options: https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types
            # Wildcards(*) are not supported!
            types:
              - text/html
            # checkMimeAccept is a boolean. If true, the Accept header will be checked for the MIME type
            checkMimeAccept: true
            # checkMimeContentType is a boolean. If true, the Content-Type header will be checked for the MIME type
            checkMimeContentType: true
            # checkAcceptEncoding is a boolean. If true, the Accept-Encoding header will be checked for the encoding
            checkAcceptEncoding: true
            # checkContentEncoding is a boolean. If true, the Content-Encoding header will be checked for the encoding
            checkContentEncoding: true
  services:
    my-service:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1"
```

## Development

The repository uses Go 1.27.4. GitHub Actions builds and tests on native Linux
AMD64 and ARM64 in Debian Trixie containers when commits are pushed to an open
pull request. The development container and Traefik smoke-test containers also
use Debian Trixie.

```sh
make build test
make lint        # golangci-lint v2.15.0
make yaegi_test  # Yaegi v0.16.3
bash scripts/smoke-test.sh
```

The smoke test runs Traefik 3.7.19 and whoami 1.12.0 in Docker Compose and
checks that Traefik rewrites the upstream response from `Name: bar` to
`Name: foo`.

Brotli is pinned at v1.1.1, the newest version compatible with Traefik
3.7.19's Yaegi v0.16.3. Brotli v1.2.0 and later require the Go builtin
`max`, which that interpreter cannot resolve (`undefined: max`). Keep the
Yaegi and Traefik tests when upgrading Brotli.

The release workflow checks pushes to `main` for an associated merged PR. It
processes eligible PRs in the order they land on `main` and uses their original
Conventional Commits to select versions and write release notes. The initial
version is `v0.1.0`. GitHub provides the tagged plugin source as the release
archive, and Traefik discovers releases from repositories with the
[`traefik-plugin` topic](https://plugins.traefik.io/create).
