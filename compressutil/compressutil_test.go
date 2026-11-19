package compressutil_test

import (
	"bytes"
	"testing"

	"github.com/michibiki-io/traefik-plugin-rewritebody/compressutil"
)

type TestStruct struct {
	desc        string
	input       []byte
	expected    []byte
	encoding    string
	shouldMatch bool
}

func TestEncode(t *testing.T) {
	input := []byte("foo is the new bar")
	for _, encoding := range []string{
		compressutil.Identity, compressutil.Gzip, compressutil.Deflate, compressutil.Brotli,
	} {
		t.Run(encoding, func(t *testing.T) {
			encoded, err := compressutil.Encode(input, encoding)
			if err != nil {
				t.Fatalf("encode: %v", err)
			}
			if bytes.Equal(input, encoded) != (encoding == compressutil.Identity) {
				t.Errorf("unexpected identity result for %s: %v", encoding, encoded)
			}

			// The Go toolchain may emit different valid compressed bytes.
			decoded, err := compressutil.Decode(bytes.NewBuffer(encoded), encoding)
			if err != nil {
				t.Fatalf("decode %s: %v", encoding, err)
			}
			if !bytes.Equal(decoded, input) {
				t.Errorf("decoded %q, want %q", decoded, input)
			}
		})
	}
}

func TestDecode(t *testing.T) {
	var (
		deflatedBytes = []byte{
			74, 203, 207, 87, 200, 44, 86, 40, 201, 72, 85,
			200, 75, 45, 87, 72, 74, 44, 2, 4, 0, 0, 255, 255,
		}
		gzippedBytes = []byte{
			31, 139, 8, 0, 0, 0, 0, 0, 0, 255, 74, 203, 207, 87, 200, 44, 86, 40, 201, 72, 85,
			200, 75, 45, 87, 72, 74, 44, 2, 4, 0, 0, 255, 255, 251, 28, 166, 187, 18, 0, 0, 0,
		}
		bredBytes = []byte{
			139, 8, 128, 102, 111, 111, 32, 105, 115, 32, 116,
			104, 101, 32, 110, 101, 119, 32, 98, 97, 114, 3,
		}
		normalBytes = []byte("foo is the new bar")
	)

	tests := []TestStruct{
		{
			desc:        "should support identity",
			input:       normalBytes,
			expected:    normalBytes,
			encoding:    compressutil.Identity,
			shouldMatch: true,
		},
		{
			desc:        "should support gzip",
			input:       gzippedBytes,
			expected:    normalBytes,
			encoding:    compressutil.Gzip,
			shouldMatch: false,
		},
		{
			desc:        "should support deflate",
			input:       deflatedBytes,
			expected:    normalBytes,
			encoding:    compressutil.Deflate,
			shouldMatch: false,
		},
		{
			desc:        "should support brotli",
			input:       bredBytes,
			expected:    normalBytes,
			encoding:    "br",
			shouldMatch: false,
		},
	}

	for _, test := range tests {
		t.Run(test.desc, func(t *testing.T) {
			output, err := compressutil.Decode(bytes.NewBuffer(test.input), test.encoding)
			if err != nil {
				t.Errorf("unexpected error: %v", err)
			}

			isBad := !bytes.Equal(test.expected, output)

			if isBad {
				t.Errorf("expected error got body: %v\n wanted: %v", output, test.expected)
			}

			if test.shouldMatch {
				isBad = !bytes.Equal(test.input, output)
			} else {
				isBad = bytes.Equal(test.input, output)
			}

			if isBad {
				t.Errorf("match error got body: %s\n wanted: %s", output, test.input)
			}
		})
	}
}
