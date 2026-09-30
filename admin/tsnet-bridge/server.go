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

// installAndroidNetworkIntegration configures Tailscale's Android-safe
// interface enumeration and supplies the active Android network interface
// as the default route interface. Android blocks the normal Linux netlink
// route/interface paths used by Tailscale.
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

		// Select the first active non-loopback interface that has
		// an IPv4 address. On the test device this is wlan0.
		if defaultInterface == "" &&
			ifs[i].Flags&net.FlagUp != 0 &&
			ifs[i].Flags&net.FlagLoopback == 0 {
			for _, addr := range addrs {
				if ip, _, err := net.ParseCIDR(addr.String()); err == nil && ip.To4() != nil {
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

	// Android blocks the normal Linux netlink route/interface paths.
	// Configure the Android-safe interface provider and default route
	// before creating/up-ing the tsnet server.
	if err := installAndroidNetworkIntegration(); err != nil {
		s.fail(err)
		return fmt.Errorf("install Android network integration: %w", err)
	}

	ts := &tsnet.Server{
		Dir:      s.stateDir,
		Hostname: s.hostname,
		AuthKey:  s.authKey,
		Logf:     func(format string, args ...any) {},
	}

	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
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
