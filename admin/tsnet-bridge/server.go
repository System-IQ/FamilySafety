package tsnetbridge

import (
	"context"
	"fmt"
	"net"
	"os"
	"sync"
	"time"

	"github.com/wlynxg/anet"
	_ "golang.org/x/mobile/bind"
	"tailscale.com/net/netmon"
	"tailscale.com/tsnet"
)

type Server struct {
	mu           sync.RWMutex
	stateDir     string
	hostname     string
	authKey      string
	ts           *tsnet.Server
	removeTunnel func()
	running      bool
	status       string
}

func NewServer(stateDir, hostname, authKey string) *Server {
	return &Server{
		stateDir: stateDir,
		hostname: hostname,
		authKey:  authKey,
		status:   "idle",
	}
}

func (s *Server) Status() string {
	s.mu.RLock()
	defer s.mu.RUnlock()

	return s.status
}

func (s *Server) IsRunning() bool {
	s.mu.RLock()
	defer s.mu.RUnlock()

	return s.running && s.ts != nil
}

// installAndroidNetworkIntegration provides Tailscale with Android-safe
// interface discovery through anet instead of Linux netlink.
//
// Android restricts the normal Linux netlink route/interface paths.
// We therefore enumerate interfaces and addresses using anet, then
// register the result with Tailscale's netmon package.
func installAndroidNetworkIntegration() error {
	ifs, err := anet.Interfaces()
	if err != nil {
		return fmt.Errorf("anet.Interfaces: %w", err)
	}

	ret := make([]netmon.Interface, 0, len(ifs))
	defaultInterface := ""

	for i := range ifs {
		addrs, err := anet.InterfaceAddrsByInterface(&ifs[i])
		if err != nil {
			return fmt.Errorf(
				"interface[%d] Addrs: %w",
				i,
				err,
			)
		}

		ret = append(ret, netmon.Interface{
			Interface: &ifs[i],
			AltAddrs:  addrs,
		})

		// Automatically choose the first active, non-loopback
		// interface that has an IPv4 address.
		if defaultInterface == "" &&
			ifs[i].Flags&net.FlagUp != 0 &&
			ifs[i].Flags&net.FlagLoopback == 0 {

			for _, addr := range addrs {
				ip, _, parseErr := net.ParseCIDR(addr.String())
				if parseErr != nil {
					continue
				}

				if ip.To4() != nil {
					defaultInterface = ifs[i].Name
					break
				}
			}
		}
	}

	if defaultInterface != "" {
		netmon.UpdateLastKnownDefaultRouteInterface(defaultInterface)
	}

	netmon.RegisterInterfaceGetter(func() ([]netmon.Interface, error) {
		return ret, nil
	})

	return nil
}

// Start initializes and starts the embedded Tailscale node.
//
// Startup order is deliberately strict:
//
//  1. Validate state directory.
//  2. Create private state directory.
//  3. Create and verify dedicated log directory.
//  4. Configure TS_LOGS_DIR.
//  5. Install Android network integration.
//  6. Construct tsnet.Server.
//  7. Call ts.Up() with a bounded timeout.
//  8. Publish running state only after successful Up().
func (s *Server) Start() (err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("tsnet start panic: %v", r)
			s.fail(err)
		}
	}()

	// ------------------------------------------------------------
	// 0. Prevent duplicate starts.
	// ------------------------------------------------------------
	s.mu.Lock()

	if s.running && s.ts != nil {
		s.mu.Unlock()
		return nil
	}

	s.status = "starting"
	s.mu.Unlock()

	// ------------------------------------------------------------
	// 1. Validate state directory.
	// ------------------------------------------------------------
	if s.stateDir == "" {
		err := fmt.Errorf("state directory is empty")
		s.fail(err)
		return err
	}

	// ------------------------------------------------------------
	// 2. Create the private application state directory.
	// ------------------------------------------------------------
	if err := os.MkdirAll(s.stateDir, 0o700); err != nil {
		s.fail(err)
		return fmt.Errorf("create state directory: %w", err)
	}

	if err := os.Chmod(s.stateDir, 0o700); err != nil {
		s.fail(err)
		return fmt.Errorf(
			"set state directory permissions: %w",
			err,
		)
	}

	// ------------------------------------------------------------
	// 3. Create and configure a dedicated Tailscale log directory.
	//
	// Result:
	//
	// stateDir/
	// ├── tailscaled.state
	// ├── tailscaled.log.conf
	// └── logs/
	//
	// This prevents logpolicy from falling back to inaccessible
	// Android filesystem locations.
	// ------------------------------------------------------------
	if _, err := configureTailscaleLogDir(s.stateDir); err != nil {
		s.fail(err)
		return fmt.Errorf(
			"configure Tailscale log directory: %w",
			err,
		)
	}

	// ------------------------------------------------------------
	// 4. Install Android-safe network integration.
	// ------------------------------------------------------------
	if err := installAndroidNetworkIntegration(); err != nil {
		s.fail(err)
		return fmt.Errorf(
			"install Android network integration: %w",
			err,
		)
	}

	// ------------------------------------------------------------
	// 5. Construct the embedded tsnet server.
	// ------------------------------------------------------------
	ts := &tsnet.Server{
		Dir:      s.stateDir,
		Hostname: s.hostname,
		AuthKey:  s.authKey,

		// Verbose backend logs are intentionally disabled at this
		// bridge layer. Tailscale's persistent log configuration and
		// buffer storage use TS_LOGS_DIR configured above.
		Logf: func(format string, args ...any) {},
	}

	// ------------------------------------------------------------
	// 6. Start Tailscale with a bounded startup timeout.
	// ------------------------------------------------------------
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

	// ------------------------------------------------------------
	// 7. Publish the running state only after ts.Up succeeds.
	// ------------------------------------------------------------
	s.mu.Lock()
	s.ts = ts
	s.running = true
	s.status = "running"
	s.mu.Unlock()

	return nil
}

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
