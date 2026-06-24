# 0006 - Send direct from Server #1; residential proxy is a fallback, not the default

Status: accepted (2026-06-24)

The Batch Runner sends direct from Server #1's own IP by default. The ProxyBase residential
proxy is NOT on the default send path; it is reserved as a fallback for sites that block the
direct IP. This reverses the earlier working assumption ("run on Server #1 through the
residential proxy") after live evidence.

The evidence (2026-06-24, identical Tidio store slice on Server #1):
- Through the residential proxy: 0 of 9 qualified sends delivered - the rotating proxy fails
  the browser CONNECT tunnel (ERR_TUNNEL_CONNECTION_FAILED) and is too slow, so Tidio times
  out (no_tidio_api). The known-good store talleyandtwine also failed via the proxy.
- Direct (no proxy): 2 of 11 delivered, wire-confirmed, including a store that had failed via
  the proxy. talleyandtwine delivers direct every time.
The proxy is fine for simple requests fetches but unreliable for the live browser sessions a
send needs. This matches Aerocrawl's own design: it uses the residential proxy only as a
fallback tier for blocked sites, never as the primary path.

Why it is recorded here: it is hard to reverse for future plans (it overturns an explicit
earlier choice, so without this record an AFK agent or a "use the proxy we pay for" reflex
will re-route everything through it and silently drop delivery to ~0), surprising without
context (we provisioned the proxy specifically to dodge datacenter-IP blocks, so "turn it
off" looks wrong), and a real trade-off (direct gives far higher delivery and zero proxy
bandwidth cost, but loses coverage on the subset of sites that block the datacenter IP - those
become retryable/Dead until a per-failure proxy-fallback is built). This ADR stops the proxy
from being put back on the default send path.
