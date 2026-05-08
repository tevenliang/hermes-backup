# OpenClaw Gateway Uninstall — Session Log

## Problem
OpenClaw gateway running as LaunchAgent (PID 22093) needed to be stopped. Plain `kill PID` did not work — process kept restarting.

## Wrong approach tried
```
$ openclaw service uninstall
error: unknown command 'service'
(Did you mean devices?)
```
`service` is not a valid subcommand.

## Correct approach
```
$ openclaw gateway uninstall
Warning: launchctl stop did not fully stop the service; used bootout fallback and left service unloaded
Stopped LaunchAgent (degraded): gui/501/ai.openclaw.gateway
LaunchAgent remains at /Users/twliang/Library/LaunchAgents/ai.openclaw.gateway.plist (could not move)

$ kill 22093
# Already gone after uninstall — launchd no longer watching
```

## Verification
```
$ ps aux | grep -E "(openclaw|hermes)" | grep -v grep
twliang  21879  0.2 1.9  Hermes gateway  ← only Hermes remains
twliang  33083  1.1 0.3  Hermes dashboard
```

## Key diagnostic commands
```bash
# Check what's running
ps aux | grep -E "(openclaw|hermes)" | grep -v grep

# Check LaunchAgent status
openclaw gateway status

# Proper uninstall sequence
openclaw gateway uninstall
```

## Related context
- OpenClaw gateway port: 18789
- Hermes gateway: different port, managed by hermes-cli
- Conflict scenario: both gateways with same Feishu channel = channel instability
