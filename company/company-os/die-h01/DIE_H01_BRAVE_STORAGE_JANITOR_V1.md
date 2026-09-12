# DIE-H01 Brave Storage and Janitor Capacity Gate v1

Status: **H01-024 acceptance candidate**
Date: 2026-09-12

## Purpose

H01-024 adds a fail-closed storage gate and a bounded Brave cache janitor without changing the canonical 20 UDD x 5 persistent profiles topology. Storage expansion can satisfy the gate because admission is based on actual free bytes, not by reducing or remapping the 100-profile fabric.

The gate is deployed at `/opt/die/h01/bin/h01-brave-storage-gate` and the accepted Brave launcher `/opt/die/h01/bin/h01-brave-profile` invokes `admit` before browser start.

## Capacity policy

- Canonical topology remains 20 UDDs x 5 persistent profiles = 100 profiles.
- Founder hard cap: at most **5 live Brave profiles** at the present stage.
- Minimum filesystem free-space reserve: **20 GiB**.
- Populated-profile measurement threshold: **16 MiB**.
- Conservative forecast per additional live profile: `max(largest observed populated profile, 512 MiB)`.
- Required free bytes are `20 GiB + remaining live slots * forecast_per_profile`.
- Admission fails closed when live count is already 5 or available space falls below the required free bytes.
- Adding disk capacity increases available bytes and can satisfy admission without changing topology.

## Live baseline

Before janitor execution the root filesystem reported:

- total: 133,569,777,664 bytes;
- used: 44,491,853,824 bytes;
- free: 82,245,664,768 bytes;
- utilization: 36%.

All 100 profile identities exist. Only two exceeded the 16 MiB growth threshold:

- `h01-web-p001`: 317,739,008 bytes;
- `h01-web-p006`: 31,272,960 bytes.

No Brave process was active. The capacity gate admitted work with a 512 MiB conservative forecast and required free capacity of 24,159,191,040 bytes, far below the observed free space.

## Janitor allowlist

The janitor may remove only the following regenerable cache locations while the owning UDD is closed and the UDD lock is successfully acquired:

- profile `Cache`;
- profile `Code Cache`;
- profile `GPUCache`;
- profile `DawnGraphiteCache`;
- profile `DawnWebGPUCache`;
- UDD `GPUPersistentCache/GPUCache`.

The janitor refuses execution when a Brave process uses the UDD or when the H01 UDD mutex is held.

## Protected authentication/session state

The janitor never targets or reads the contents of authentication/session stores. Protected root names include:

`Cookies`, `Local Storage`, `IndexedDB`, `WebStorage`, `Session Storage`, `Sessions`, `Service Worker`, `Login Data`, `Login Data For Account`, `Preferences`, `Secure Preferences`, `Network`, `GCM Store`, `Sync Data`, `BraveWallet`, `Extension State`, `File System`, and `ClientCertificates`.

Directory existence may be observed for safety verification; credential values, cookies, tokens and session bytes are not read.

## Live bounded janitor proof

For closed/unlocked `h01-web-s01` / `h01-web-p001`, dry-run measured 258,408,448 bytes of allowlisted cache. The same allowlist was then executed under the UDD mutex.

After execution:

- all allowlisted profile cache directories were absent;
- protected authentication/session roots remained present;
- free space increased to 82,504,069,120 bytes;
- p001 shrank to 59,359,232 bytes;
- p006 remained 31,272,960 bytes;
- populated-profile count remained 2;
- capacity admission remained PASS;
- no `/srv/die` mutation occurred.

The free-space delta was 258,404,352 bytes; the 4 KiB difference from `du` reclaimable bytes is filesystem accounting granularity.

## Host deployment / rollback

The previous launcher was preserved at:

`/var/lib/die/h01/rollback/H01-024/h01-brave-profile.pre-h01-024`

Its SHA-256 exactly matches the pre-change launcher SHA. The new launcher fails closed if the storage gate executable is missing or if `admit` does not pass.

This task grants no storage-purchase/spend authority. Founder-approved expansion planned for the following week remains a separate action.
