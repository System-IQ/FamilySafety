# tsnet-bridge

Embeds [Tailscale tsnet](https://tailscale.com/kb/1244/tsnet) into the
Family Safety Admin Android app, in **userspace networking mode**.

## Why

- Does NOT use Android `VpnService` → no conflict with other VPN apps.
- Provides a stable tailnet IP (`100.x.y.z`) that never changes.
- Works from any network (4G, home WiFi, abroad).
- WireGuard-encrypted by default.

## What it does

1. Brings up a tsnet node with a given hostname and auth key.
2. Listens on the tailnet at a chosen port.
3. Reverse-proxies every HTTP request to a local target
   (typically a FastAPI server running via Chaquopy on 127.0.0.1:8001).

## Build

Built automatically by GitHub Actions:

    .github/workflows/build-tsnet-bridge.yml

Output: `tsnetbridge.aar` artifact (arm64-v8a only).

## Kotlin usage

    val server = tsnetbridge.NewServer(
        stateDir = filesDir.resolve("tsnet").absolutePath,
        hostname = "admin-phone",
        authKey  = "<tskey-auth-xxxx>",
    )
    server.Start()
    val ip = server.IP4()             // e.g. "100.75.42.9"
    server.ListenAndProxy(8000, "http://127.0.0.1:8001")
    // ... later
    server.Stop()
