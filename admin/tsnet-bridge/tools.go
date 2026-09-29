//go:build tools
// +build tools

// Canonical "tools.go" pattern from the Go project.
// This file is NOT compiled into the app. It exists so that
// `go mod tidy` keeps golang.org/x/mobile in go.mod, which
// `gomobile bind` requires to be present in the module graph.
//
// Reference: https://github.com/golang/go/wiki/Modules#how-can-i-track-tool-dependencies-for-a-module
package tools

import (
_ "golang.org/x/mobile/cmd/gobind"
_ "golang.org/x/mobile/cmd/gomobile"
)
