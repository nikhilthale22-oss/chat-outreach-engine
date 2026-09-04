# Pool + capacity (measured 2026-06-30)

One-way model: we only DELIVER the pitch. Capacity = pool x delivery-rate, and each store gets ONE
pitch, so the **pool is the ceiling** (not throughput - one Server #1 box does ~500-1,500 delivered/day).

## Tagged-pool per vendor (StoreLeads, ~574k tagged rows, domain-deduped)

| vendor | tagged | vendor | tagged |
|---|--:|---|--:|
| shopify-inbox | 73,514 | chatra | 1,002 |
| gorgias | 6,220 | reamaze | 848 |
| tidio | 5,498 | livechat | 681 |
| zendesk | 3,961 | helpscout | 357 |
| tawk | 1,269 | crisp | 275 |
| intercom | 1,229 | **total drivable** | **~94k** |

Untapped, drivable, QUALIFIED (no existing AI), ~2.5k: richpanel 578, freshchat 528, freshdesk 447,
zoho salesiq 268, kustomer 245, olark 218, gladly 196.
Excluded (store already has a bot - disqualified): ChatBot 818, FB Messenger 1,205, ManyChat 250,
Gobot 105, Drift 54.

## Measured deliverable capacity NOW (~14.5k, ~97% Shopify Inbox)

- **Shopify Inbox ~14,000-38,000** = 73,514 x ~19-52% (MEASURED: 15/80 on one run, 24-39/75 on another;
  free datacenter path). CORRECTED 2026-07-15: losses are ADAPTER ROBUSTNESS (widget absent on stale
  tags, strict confirm, form/launcher variants), NOT captcha - the 75-store run had 0 captcha challenges.
  There is NO "passive hCaptcha silently rejects half / decays 67->48% from one IP" effect (misread of
  form_blocked).
- **Tidio ~420** = 5,498 x 7.6% (MEASURED N=40). Everything else is verify-to-composer (reach proven,
  delivery rate NOT yet): Zendesk ~600 est, Tawk ~300, Chatra ~150, Crisp ~80, LiveChat ~35. Gorgias /
  Intercom API wired-but-unverified.

## The 8M "main file" is NOT a cheap pool

`combined_domains.csv` = 8,021,554 rows, **domain + platform only** (4.48M woo + 3.54M shopify), no
chat tags. Feasibility test (150 random shopify, fetch+detect from Server #1): **41% fetched** (59%
blocked - datacenter IP / Cloudflare), **1% had a detectable chat vendor**. Re-scanning it is
inefficient; StoreLeads tags already did the JS-render detection.

## How to grow the pool

1. **Activate the tagged 94k:** verify Gorgias (+6,220, wired), build the untapped vendors (~2.5k),
   extract qualified per-vendor lists.
2. **Depth beyond 94k:** a richer StoreLeads export WITH the technologies/installed_apps columns (the
   8M file lacks them) + a mid-market revenue band. Not a fresh self-scan of the 8M.
