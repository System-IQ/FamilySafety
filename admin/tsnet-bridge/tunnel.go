package tsnetbridge

import (
	"errors"
	"fmt"
	"io"
	"net"
	"net/netip"
	"net/url"
	"strconv"
	"strings"
	"time"
)

// ListenAndProxy does NOT call tsnet.Listen.
//
// Instead, it registers one fallback TCP handler inside tsnet.
// Incoming traffic for proxyPort is then forwarded to the local
// HTTP service, normally 127.0.0.1:8001.
//
// This keeps the proxy entirely inside tsnet's userspace network
// stack and avoids creating a host network listener.
func (s *Server) ListenAndProxy(proxyPort int, target string) (err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("tunnel start panic: %v", r)
			s.fail(err)
		}
	}()

	if proxyPort < 1 || proxyPort > 65535 {
		return fmt.Errorf("invalid proxy port: %d", proxyPort)
	}

	targetAddr, err := parseLocalTarget(target)
	if err != nil {
		return err
	}

	s.mu.Lock()

	ts := s.ts
	running := s.running
	existing := s.removeTunnel != nil

	s.mu.Unlock()

	if !running || ts == nil {
		return errors.New("tsnet is not running")
	}

	if existing {
		return errors.New("tunnel is already running")
	}

	remove := ts.RegisterFallbackTCPHandler(
		func(src, dst netip.AddrPort) (func(net.Conn), bool) {
			_ = src

			if dst.Port() != uint16(proxyPort) {
				return nil, false
			}

			return func(conn net.Conn) {
				handleTCPProxy(conn, targetAddr)
			}, true
		},
	)

	s.mu.Lock()

	// Protect against a duplicate registration race.
	if s.removeTunnel != nil {
		s.mu.Unlock()
		remove()
		return errors.New("tunnel is already running")
	}

	s.removeTunnel = remove
	s.status = "running + tunnel"

	s.mu.Unlock()

	return nil
}

// parseLocalTarget only permits local application targets.
//
// Examples:
//
//	http://127.0.0.1:8001
//	http://localhost:8001
func parseLocalTarget(raw string) (string, error) {
	u, err := url.Parse(raw)
	if err != nil {
		return "", fmt.Errorf("invalid proxy target: %w", err)
	}

	if u.Scheme != "http" && u.Scheme != "https" {
		return "", fmt.Errorf("unsupported proxy target scheme: %q", u.Scheme)
	}

	host := strings.ToLower(u.Hostname())

	if host != "localhost" &&
		host != "127.0.0.1" &&
		host != "::1" {
		return "", fmt.Errorf(
			"proxy target must be local, got %q",
			u.Hostname(),
		)
	}

	port := u.Port()

	if port == "" {
		if u.Scheme == "https" {
			port = "443"
		} else {
			port = "80"
		}
	}

	n, err := strconv.Atoi(port)
	if err != nil || n < 1 || n > 65535 {
		return "", fmt.Errorf("invalid target port: %q", port)
	}

	return net.JoinHostPort(u.Hostname(), strconv.Itoa(n)), nil
}

// handleTCPProxy forwards the complete TCP stream.
//
// HTTP requests remain untouched; they pass through as ordinary TCP bytes.
func handleTCPProxy(in net.Conn, targetAddr string) {
	defer func() {
		_ = in.Close()

		if recover() != nil {
			// Never allow a connection-handler panic to cross the
			// gomobile/native boundary.
		}
	}()

	out, err := net.DialTimeout("tcp", targetAddr, 5*time.Second)
	if err != nil {
		return
	}

	defer out.Close()

	done := make(chan struct{}, 2)

	go copyStream(out, in, done)
	go copyStream(in, out, done)

	<-done
	<-done
}

func copyStream(dst net.Conn, src net.Conn, done chan<- struct{}) {
	defer func() {
		done <- struct{}{}
	}()

	_, _ = io.Copy(dst, src)
}
