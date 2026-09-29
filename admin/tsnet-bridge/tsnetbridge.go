// Package tsnetbridge embeds Tailscale tsnet into an Android app.
//
// Design:
//   - Runs entirely in userspace networking mode (no VpnService).
//   - Provides a simple Start/Stop/Status API to Kotlin.
//   - Acts as an HTTP reverse proxy from the tailnet to a local
//     FastAPI server (typically on 127.0.0.1:8001).
//
// Build:
//   gomobile bind -target=android -androidapi 24 \
//       -o tsnetbridge.aar ./tsnet-bridge
//
// The resulting AAR exposes:
//   tsnetbridge.NewServer(stateDir, hostname, authKey) *Server
//   server.Start() error
//   server.Stop()
//   server.Status() string
//   server.IP4() string
//   server.ListenAndProxy(port int, target string) error
package tsnetbridge

import (
	// Blank import: keeps golang.org/x/mobile in go.mod
	// across go mod tidy. Required by gomobile bind.
	_ "golang.org/x/mobile/bind"
"context"
"fmt"
"io"
"net"
"net/http"
"os"
"sync"
"time"

"tailscale.com/tsnet"
)

// Server wraps a tsnet.Server with lifecycle management and a
// simple HTTP reverse-proxy from the tailnet to a local target.
type Server struct {
mu       sync.Mutex
ts       *tsnet.Server
stateDir string
hostname string
authKey  string
status   string
running  bool
proxySrv *http.Server
proxyLn  net.Listener
}

// NewServer creates a new tsnet Server handle.
//
//   - stateDir : persistent storage (Android filesDir, e.g. "/data/data/.../files/tsnet")
//   - hostname : display name in the tailnet (e.g. "admin-phone")
//   - authKey  : Tailscale auth key (tskey-auth-xxxx). Empty => interactive login URL printed to logs.
func NewServer(stateDir, hostname, authKey string) *Server {
return &Server{
stateDir: stateDir,
hostname: hostname,
authKey:  authKey,
status:   "idle",
}
}

// Status returns a human-readable status string.
func (s *Server) Status() string {
s.mu.Lock()
defer s.mu.Unlock()
return s.status
}

// IsRunning reports whether tsnet is currently up.
func (s *Server) IsRunning() bool {
s.mu.Lock()
defer s.mu.Unlock()
return s.running
}

// Start brings tsnet up. Blocks until the node has a tailnet IP
// or until the context timeout (90s) expires.
func (s *Server) Start() error {
s.mu.Lock()
defer s.mu.Unlock()
if s.running {
return nil
}

if err := os.MkdirAll(s.stateDir, 0o700); err != nil {
s.status = "error: mkdir: " + err.Error()
return err
}

ts := &tsnet.Server{
Dir:      s.stateDir,
Hostname: s.hostname,
AuthKey:  s.authKey,
Logf:     func(format string, args ...any) {}, // silent
}

ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
defer cancel()

st, err := ts.Up(ctx)
if err != nil {
s.status = "error: up: " + err.Error()
return err
}

s.ts = ts
s.running = true
s.status = "running: " + string(st.BackendState)
return nil
}

// Stop shuts down the proxy and tsnet.
func (s *Server) Stop() {
s.mu.Lock()
defer s.mu.Unlock()

if s.proxyLn != nil {
_ = s.proxyLn.Close()
s.proxyLn = nil
}
if s.proxySrv != nil {
ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
_ = s.proxySrv.Shutdown(ctx)
cancel()
s.proxySrv = nil
}
if s.ts != nil {
_ = s.ts.Close()
s.ts = nil
}
s.running = false
s.status = "stopped"
}

// IP4 returns the first tailnet IPv4 address (empty if not running).
func (s *Server) IP4() string {
s.mu.Lock()
defer s.mu.Unlock()
if s.ts == nil {
return ""
}
ips, err := s.ts.TailscaleIPs()
if err != nil {
return ""
}
for _, ip := range ips {
if ip.Is4() {
return ip.String()
}
}
return ""
}

// ListenAndProxy starts listening on the tailnet at the given port
// and forwards every HTTP request to `target` (e.g., "http://127.0.0.1:8001").
// Non-blocking.
func (s *Server) ListenAndProxy(port int, target string) error {
s.mu.Lock()
ts := s.ts
already := s.proxyLn != nil
s.mu.Unlock()

if ts == nil {
return fmt.Errorf("tsnet not started")
}
if already {
return fmt.Errorf("proxy already running")
}

ln, err := ts.Listen("tcp", fmt.Sprintf(":%d", port))
if err != nil {
return fmt.Errorf("listen: %w", err)
}

handler := &proxyHandler{target: target}
srv := &http.Server{
Handler:           handler,
ReadHeaderTimeout: 10 * time.Second,
}

s.mu.Lock()
s.proxyLn = ln
s.proxySrv = srv
s.mu.Unlock()

go func() {
_ = srv.Serve(ln)
}()

return nil
}

// ---------------------------------------------------------------
// HTTP reverse proxy
// ---------------------------------------------------------------

type proxyHandler struct {
target string // e.g. "http://127.0.0.1:8001"
}

func (h *proxyHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
target := h.target + r.URL.Path
if r.URL.RawQuery != "" {
target += "?" + r.URL.RawQuery
}

req, err := http.NewRequestWithContext(r.Context(), r.Method, target, r.Body)
if err != nil {
http.Error(w, "upstream request build: "+err.Error(), http.StatusBadGateway)
return
}
req.Header = r.Header.Clone()
req.Header.Del("Connection")

resp, err := http.DefaultClient.Do(req)
if err != nil {
http.Error(w, "upstream: "+err.Error(), http.StatusBadGateway)
return
}
defer resp.Body.Close()

for k, vs := range resp.Header {
for _, v := range vs {
w.Header().Add(k, v)
}
}
w.WriteHeader(resp.StatusCode)
_, _ = io.Copy(w, resp.Body)
}
