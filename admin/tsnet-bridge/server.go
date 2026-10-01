// Package tsnetbridge embeds Tailscale tsnet into an Android app.
//
// Goals:
//   - userspace networking (no VpnService; no VPN conflict)
//   - multi-instance (one per profile: kids / wife / ...)
//   - respects TS_LOGS_DIR for writable state (Android sandbox)
//   - exposes a simple Start/Stop/Status API to Kotlin via gomobile
//
// Funnel is NOT enabled here (tsnet has no stable public Funnel API in
// v1.88). It will be added in a future phase via LocalClient().
package tsnetbridge

import (
"context"
"fmt"
"io"
"net"
"net/http"
"os"
"path/filepath"
"strings"
"sync"
"time"

"tailscale.com/tsnet"
)

// Server is one tsnet node (one profile).
type Server struct {
mu       sync.Mutex
instance string
ts       *tsnet.Server
stateDir string
hostname string
authKey  string
status   string
running  bool

proxySrv *http.Server
proxyLn  net.Listener
proxyTgt string
proxyPort int
}

// NewServer creates an independent tsnet node.
func NewServer(instance, stateDir, hostname, authKey string) *Server {
return &Server{
instance: instance,
stateDir: stateDir,
hostname: hostname,
authKey:  authKey,
status:   "idle",
}
}

// ----------------------------------------------------------------
// Getters
// ----------------------------------------------------------------

func (s *Server) Status() string {
s.mu.Lock()
defer s.mu.Unlock()
return s.status
}

func (s *Server) IsRunning() bool {
s.mu.Lock()
defer s.mu.Unlock()
return s.running
}

func (s *Server) LogFilePath() string {
return filepath.Join(s.stateDir, "tsnet.log")
}

func (s *Server) TailnetHostname() string {
s.mu.Lock()
defer s.mu.Unlock()
return s.hostname
}

// IP4 returns the tailnet IPv4 ("" if not running).
func (s *Server) IP4() string {
s.mu.Lock()
ts := s.ts
s.mu.Unlock()
if ts == nil {
return ""
}
ip4, _ := ts.TailscaleIPs()
if !ip4.IsValid() || !ip4.Is4() {
return ""
}
return ip4.String()
}

func (s *Server) ProxyPort() int {
s.mu.Lock()
defer s.mu.Unlock()
return s.proxyPort
}

// ----------------------------------------------------------------
// Lifecycle
// ----------------------------------------------------------------

func (s *Server) Start() error {
s.mu.Lock()
if s.running {
s.mu.Unlock()
return nil
}
s.mu.Unlock()

if err := os.MkdirAll(s.stateDir, 0o700); err != nil {
s.setStatus("error: mkdir: " + err.Error())
return err
}

// tsnet uses $TS_LOGS_DIR on some code paths.
os.Setenv("TS_LOGS_DIR", s.stateDir)

ts := &tsnet.Server{
Dir:      s.stateDir,
Hostname: s.hostname,
AuthKey:  s.authKey,
Logf: func(format string, args ...any) {
s.writeLog("tsnet: " + fmt.Sprintf(format, args...))
},
UserLogf: func(format string, args ...any) {
s.writeLog("user: " + fmt.Sprintf(format, args...))
},
}

ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
defer cancel()

s.writeLog(fmt.Sprintf("start: instance=%s hostname=%s", s.instance, s.hostname))

st, err := ts.Up(ctx)
if err != nil {
s.setStatus("error: up: " + err.Error())
s.writeLog("ts.Up failed: " + err.Error())
return err
}

s.mu.Lock()
s.ts = ts
s.running = true
s.status = "running: " + string(st.BackendState)
s.mu.Unlock()
s.writeLog("ts.Up succeeded: " + string(st.BackendState))
return nil
}

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
s.writeLog("stopped")
}

// ----------------------------------------------------------------
// Proxy: tailnet :port  ->  target (e.g. http://127.0.0.1:8000)
// ----------------------------------------------------------------

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

srv := &http.Server{
Handler:           &proxyHandler{target: target},
ReadHeaderTimeout: 10 * time.Second,
}

s.mu.Lock()
s.proxyLn = ln
s.proxySrv = srv
s.proxyTgt = target
s.proxyPort = port
s.mu.Unlock()

go func() { _ = srv.Serve(ln) }()
s.writeLog(fmt.Sprintf("proxy: :%d -> %s", port, target))
return nil
}

// ----------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------

func (s *Server) setStatus(v string) {
s.mu.Lock()
s.status = v
s.mu.Unlock()
}

// ----------------------------------------------------------------
// HTTP reverse proxy
// ----------------------------------------------------------------

type proxyHandler struct {
target string
}

func (h *proxyHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
fullURL := h.target + r.URL.Path
if r.URL.RawQuery != "" {
fullURL += "?" + r.URL.RawQuery
}
req, err := http.NewRequestWithContext(r.Context(), r.Method, fullURL, r.Body)
if err != nil {
http.Error(w, "upstream build: "+err.Error(), http.StatusBadGateway)
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

// Keep "strings" imported even if unused paths change.
var _ = strings.TrimSpace
