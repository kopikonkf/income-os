# DIE H01 Brave Fabric Provisioner v1

Status: H01-023 DONE / PASS
Date: 2026-09-12

## Purpose

H01-023 canonicalizes the already-live Brave fabric provisioner for the fixed topology approved by H01-021: 20 UDDs with five mapped persistent profile identities each, for 100 profile identities total.

The provisioner creates directory/layout state and merges a stateless UI-preferences template. It does not clone an authenticated browser profile and does not read or copy cookie, token, session, login, IndexedDB, Local Storage, Service Worker or other authentication/session stores.

## Canonical mapping

For profile number `n` in `1..100`:

- `udd_index = floor((n-1)/5)+1`
- `slot = ((n-1) mod 5)+1`
- UDD = `h01-web-s01` through `h01-web-s20`
- profile = `h01-web-p001` through `h01-web-p100`
- CDP = `127.0.0.1:9201` through `127.0.0.1:9300`
- exactly five profile identities map to each UDD

The provisioner writes `state=PROVISIONED_NOT_AUTHENTICATED`; authentication remains Founder-provided and incremental/on-demand.

## Live implementation parity

Repository source `engineering/brave_fabric_provision.py` is byte-identical to `/opt/die/h01/bin/h01-brave-provision` at acceptance. Repository fixture `fixtures/h01-023/profile-preferences-template.json` is byte-identical to `/etc/die/h01/brave/profile-preferences-template.json`.

The preference template contains only UI configuration for bookmark bar, Brave NTP/search/news/rewards/stats/together/today and translate behavior. It contains no credential/session material.

## Acceptance

Live `h01-brave-provision validate` returns PASS with:

- UDD count: 20
- profile count: 100
- CDP range: 9201-9300
- errors: none

Static safety tests reject secret-store cloning primitives and secret-store names in source/template. The live fabric manifest contains exactly 20 UDDs and exactly five profile rows per UDD.

H01-023 does not authenticate profiles, launch Web-AI providers, purchase storage, or grant submission/publication authority.
