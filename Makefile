.PHONY: default build lint test yaegi_test vendor clean

default: lint test

build:
	go build -mod=vendor ./...

lint:
	golangci-lint run

test:
	go test -mod=vendor -v -cover ./...

yaegi_test:
	@set -eu; \
	root="$$(pwd)"; module="$$(go list -m)"; gopath="$$(mktemp -d)"; \
	trap 'rm -rf "$$gopath"' EXIT; \
	mkdir -p "$$gopath/src/$$(dirname "$$module")"; \
	ln -s "$$root" "$$gopath/src/$$module"; \
	cd "$$gopath/src/$$module"; \
	GOPATH="$$gopath" yaegi test -v .

vendor:
	go mod vendor

clean:
	rm -rf ./vendor
