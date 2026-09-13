# DIE H01 Daily Provider Thread Policy V1

## Purpose

Use one durable human-like conversation thread per Web-AI provider and authenticated profile for one Jakarta calendar day. H01 currently has one READY authenticated profile (`h01-web-p001`), therefore operationally this is exactly one thread per provider per day.

## Clock and rollover

- Canonical timezone: `Asia/Jakarta` / WIB / UTC+7.
- Daily window: `00:00:00` through `23:59:59.999...` WIB.
- Rollover is exact at Jakarta midnight. `17:00:00Z` starts the next Jakarta day.
- A provider thread never carries into the next Jakarta date; the first committed prompt after rollover establishes the next daily thread.

## Dispatch invariant

For each `(Jakarta date, provider_id, authenticated profile_id)`:

1. First prompt may start a new conversation.
2. After strong provider commit, persist the conversation URL and prompt/job evidence.
3. Every later prompt that day must open and append to that same conversation URL.
4. A different conversation URL for the same key is `E_DAILY_THREAD_VIOLATION` and fails closed.
5. A committed prompt is never automatically re-submitted. Recovery rechecks the same conversation or recovers the already-produced local provider output.
6. No daily-thread policy grants submission, publication, or spend authority.

## Audit ledger

Runtime registry: `/var/lib/die/h01/browser/daily-provider-threads.v1.json`.

Each daily provider/profile record preserves:

- canonical conversation URL;
- opened and last-dispatch timestamps;
- committed dispatch count;
- successful `ARTIFACT_CREATED` job count;
- success rate = successful jobs / committed dispatches;
- job IDs and unique prompt SHA-256 values.

The registry is reconstructable from durable `provider-dispatch.receipt.json` evidence if a process crashes after provider commit but before the registry sync.

## H01-108 counting rule

H01-108 acceptance remains semantic, not physical-file based: 100 unique semantic masters from the frozen 100 unique eligible nouns, with `no duplicate semantic count`. Retry variants with different SHA-256 are valuable additional inventory but do not replace a missing semantic noun position.
