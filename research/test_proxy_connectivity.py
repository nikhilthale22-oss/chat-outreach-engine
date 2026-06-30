#!/usr/bin/env python3
"""Run ON Server #1. Loads .env.proxy, confirms the proxy connects and the egress IP is residential
(not Server #1's Hetzner datacenter IP). <10KB. Prints egress IP + ASN, no credentials."""
import json, os, urllib.request

env = {}
with open("/root/chat-outreach-engine/.env.proxy") as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1); env[k] = v

server, user, pw = env["PROXY_SERVER"], env["PROXY_USERNAME"], env["PROXY_PASSWORD"]
host = server.split("://", 1)[1]
proxy_url = f"http://{user}:{pw}@{host}"
op = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url}))

# direct egress (Server #1 datacenter IP) for contrast
try:
    direct_ip = json.load(urllib.request.urlopen("https://api.ipify.org?format=json", timeout=15))["ip"]
except Exception as e:
    direct_ip = f"(direct lookup failed: {str(e)[:50]})"

try:
    prox_ip = json.load(op.open("https://api.ipify.org?format=json", timeout=30))["ip"]
except Exception as e:
    print("PROXY CONNECT FAILED:", type(e).__name__, str(e)[:160]); raise SystemExit(3)

print(f"direct egress (Server #1): {direct_ip}")
print(f"proxy  egress (ProxyBase): {prox_ip}")
print(f"changed IP: {direct_ip != prox_ip}")
try:
    info = json.load(urllib.request.urlopen(f"https://ipinfo.io/{prox_ip}/json", timeout=15))
    hosting = bool(info.get("hosting") or info.get("privacy", {}).get("hosting"))
    print(f"  org : {info.get('org','?')}")
    print(f"  loc : {info.get('city','?')}, {info.get('region','?')}, {info.get('country','?')}")
    print(f"  verdict: {'DATACENTER/hosting' if hosting else 'RESIDENTIAL/ISP (good)'}")
except Exception as e:
    print("  (ASN lookup failed:", str(e)[:80], ")")
