package tsnetbridge

import (
	"fmt"
	"os"
	"path/filepath"
)

const tailscaleLogDirEnv = "TS_LOGS_DIR"

// configureTailscaleLogDir creates a private directory dedicated
// to Tailscale log configuration and persistent log-buffer state.
func configureTailscaleLogDir(stateDir string) (string, error) {
	if stateDir == "" {
		return "", fmt.Errorf("state directory is empty")
	}

	logDir := filepath.Join(stateDir, "logs")

	if err := os.MkdirAll(logDir, 0o700); err != nil {
		return "", fmt.Errorf(
			"create Tailscale log directory %q: %w",
			logDir,
			err,
		)
	}

	if err := os.Chmod(logDir, 0o700); err != nil {
		return "", fmt.Errorf(
			"set Tailscale log directory permissions %q: %w",
			logDir,
			err,
		)
	}

	info, err := os.Stat(logDir)
	if err != nil {
		return "", fmt.Errorf(
			"stat Tailscale log directory %q: %w",
			logDir,
			err,
		)
	}

	if !info.IsDir() {
		return "", fmt.Errorf(
			"Tailscale log path %q is not a directory",
			logDir,
		)
	}

	// Verify write access before starting tsnet.
	testFile := filepath.Join(logDir, ".write-test")

	f, err := os.OpenFile(
		testFile,
		os.O_WRONLY|os.O_CREATE|os.O_TRUNC,
		0o600,
	)
	if err != nil {
		return "", fmt.Errorf(
			"Tailscale log directory is not writable %q: %w",
			logDir,
			err,
		)
	}

	if err := f.Close(); err != nil {
		_ = os.Remove(testFile)

		return "", fmt.Errorf(
			"close Tailscale log write test: %w",
			err,
		)
	}

	if err := os.Remove(testFile); err != nil {
		return "", fmt.Errorf(
			"remove Tailscale log write test: %w",
			err,
		)
	}

	// Tell Tailscale logpolicy to use the app-private directory.
	if err := os.Setenv(tailscaleLogDirEnv, logDir); err != nil {
		return "", fmt.Errorf(
			"set %s=%q: %w",
			tailscaleLogDirEnv,
			logDir,
			err,
		)
	}

	return logDir, nil
}
