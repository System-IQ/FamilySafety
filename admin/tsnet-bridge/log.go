package tsnetbridge

import (
"fmt"
"os"
"path/filepath"
"time"
)

// writeLog appends a line to stateDir/tsnet.log or $TS_LOGS_DIR/tsnet.log.
func (s *Server) writeLog(msg string) {
dir := s.stateDir
if v := os.Getenv("TS_LOGS_DIR"); v != "" {
dir = v
}
if dir == "" {
return
}
_ = os.MkdirAll(dir, 0o700)
path := filepath.Join(dir, "tsnet.log")
f, err := os.OpenFile(path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
if err != nil {
return
}
defer f.Close()

ts := time.Now().UTC().Format("2006-01-02T15:04:05.000Z")
_, _ = fmt.Fprintf(f, "[%s] [%s] %s\n", ts, s.instance, msg)
}
