# Real first-party `DEGRADED_NO_EVIDENCE` proof

This is the real runtime probe, kept separate from the controlled smoke
proof. No raw response or normalized evidence was persisted because the
source response could not be parsed as a supported Data & Trends document.

- command: `python3 company/company-os/die-h01/engineering/pond5_customer_search_acquire.py --media-type illustrations --state-root company/company-os/die-h01/evidence/h01-131c/live-first-party-degraded --query-key pond5:illustrations:live-probe:20260914`
- receipt: `sources/pond5_customer_search_data_trends_v1/queries/85ec7254f514c8486cdd565a/acquisitions/H01-ACQ-330E858FD311116EACBD3C22.json`
- status: `DEGRADED_NO_EVIDENCE`
- effective freshness: `UNKNOWN`
- error: `E_SOURCE_UNAVAILABLE` / `Pond5ParseError` / `E_POND5_NO_SUPPORTED_DATA`
- source locator: `https://contributor.pond5.com/data-trends/illustrations/`
- raw evidence: none (`bytes`, `content_type`, `relative_path`, and `sha256` are null in the receipt)

This probe did not read or export cookies, tokens, browser credentials, or
session state, and did not attempt to bypass the source robot challenge.
