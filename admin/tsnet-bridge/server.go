package tsnetbridge

import (
	"context"
	"fmt"
	"os"
	"sync"
	"time"

	_ "golang.org/x/mobile/bind"
	"tailscale.com/tsnet"
)

// Server owns exactly one embedded tsnet.Server.
//
// Lifecycle:
//
//	idle -> starting -> running -> stopping -> stopped
//
// A failed operation never changes the state to running.
type Server struct {
	mu sync.RWMutex

	stateDir string
	hostname string
	authKey  string

	ts *tsnet.Server

	removeTunnel func()

	running bool
	status  string
}

// NewServer creates an isolated embedded Tailscale node.
func NewServer(stateDir, hostname, authKey string) *Server {
	return &Server{
		stateDir: stateDir,
		hostname: hostname,
		authKey:  authKey,
		status:   "idle",
	}
}

// Status returns the current lifecycle state.
func (s *Server) Status() string {
	s.mu.RLock()
	defer s.mu.RUnlock()

	return s.status
}

// IsRunning reports whether tsnet successfully reached Running.
func (s *Server) IsRunning() bool {
	s.mu.RLock()
	defer s.mu.RUnlock()

	return s.running && s.ts != nil
}

// Start creates and starts a fresh tsnet instance.
func (s *Server) Start() (err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("tsnet start panic: %v", r)
			s.fail(err)
		}
	}()

	s.mu.Lock()

	if s.running && s.ts != nil {
		s.mu.Unlock()
		return nil
	}

	s.status = "starting"
	s.mu.Unlock()

	if err := os.MkdirAll(s.stateDir, 0o700); err != nil {
		s.fail(err)
		return fmt.Errorf("create state directory: %w", err)
	}

	ts := &tsnet.Server{
		Dir:      s.stateDir,
		Hostname: s.hostname,
		AuthKey:  s.authKey,
		Logf: func(format string, args ...any) {
			// Quiet production logging.
		},
	}

	ctx, cancel := context.WithTimeout(
		context.Background(),
		90*time.Second,
	)
	defer cancel()

	if _, err := ts.Up(ctx); err != nil {
		_ = ts.Close()
		s.fail(err)
		return fmt.Errorf("tsnet start: %w", err)
	}

	s.mu.Lock()
	s.ts = ts
	s.running = true
	s.status = "running"
	s.mu.Unlock()

	return nil
}

// Stop removes the tunnel handler first, then closes tsnet.
func (s *Server) Stop() {
	s.mu.Lock()

	ts := s.ts
	removeTunnel := s.removeTunnel

	s.ts = nil
	s.removeTunnel = nil
	s.running = false
	s.status = "stopping"

	s.mu.Unlock()

	if removeTunnel != nil {
		removeTunnel()
	}

	if ts != nil {
		_ = ts.Close()
	}

	s.mu.Lock()
	s.status = "stopped"
	s.mu.Unlock()
}

// IP4 returns the node's Tailscale IPv4 address.
func (s *Server) IP4() string {
	s.mu.RLock()
	ts := s.ts
	running := s.running
	s.mu.RUnlock()

	if !running || ts == nil {
		return ""
	}

	ip4, _ := ts.TailscaleIPs()

	if !ip4.IsValid() || !ip4.Is4() {
		return ""
	}

	return ip4.String()
}

func (s *Server) fail(err error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.running = false
	s.ts = nil
	s.removeTunnel = nil
	s.status = "error: " + err.Error()
}
