-- die.economic-ledger.sqlite.v1
-- Reference schema only. ECON-002 does not activate a live financial database.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS economic_events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  schema_version TEXT NOT NULL CHECK(schema_version='die.economic-ledger.event.v1'),
  observed_at TEXT NOT NULL,
  recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  event_type TEXT NOT NULL CHECK(event_type IN (
    'REVENUE_REALIZED','REVENUE_REFUND','REVENUE_CHARGEBACK',
    'COST_DIRECT_VARIABLE','COST_SHARED_VARIABLE','COST_GLOBAL_FIXED','COST_OTHER_NONVARIABLE',
    'FOUNDER_TIME','RESOURCE_USAGE','FX_RATE_OBSERVED','REVERSAL'
  )),
  holding_id TEXT NOT NULL,
  economic_trace_id TEXT,
  parent_task_id TEXT,
  incident_id TEXT,
  source_system TEXT NOT NULL,
  source_event_id TEXT,
  idempotency_key TEXT NOT NULL UNIQUE,
  provenance_ref TEXT NOT NULL,
  reversal_of_event_id TEXT REFERENCES economic_events(event_id),
  currency TEXT,
  amount_minor INTEGER,
  duration_minutes REAL,
  precision TEXT CHECK(precision IN ('MEASURED','ESTIMATED','UNKNOWN') OR precision IS NULL),
  founder_time_category TEXT,
  resource_class TEXT CHECK(resource_class IN ('G0','H1','H2','P1','P2','P3','P4','A1') OR resource_class IS NULL),
  usage_quantity REAL,
  usage_unit TEXT,
  fx_quote_currency TEXT,
  fx_rate_text TEXT,
  fx_rate_timestamp TEXT,
  fx_rate_source TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  CHECK(
    (event_type IN ('REVENUE_REALIZED','REVENUE_REFUND','REVENUE_CHARGEBACK','COST_DIRECT_VARIABLE','COST_SHARED_VARIABLE','COST_GLOBAL_FIXED','COST_OTHER_NONVARIABLE') AND currency IS NOT NULL AND amount_minor IS NOT NULL AND amount_minor >= 0)
    OR event_type NOT IN ('REVENUE_REALIZED','REVENUE_REFUND','REVENUE_CHARGEBACK','COST_DIRECT_VARIABLE','COST_SHARED_VARIABLE','COST_GLOBAL_FIXED','COST_OTHER_NONVARIABLE')
  ),
  CHECK(
    (event_type='FOUNDER_TIME' AND duration_minutes IS NOT NULL AND duration_minutes >= 0 AND precision IS NOT NULL AND founder_time_category IS NOT NULL)
    OR event_type!='FOUNDER_TIME'
  ),
  CHECK(
    (event_type='RESOURCE_USAGE' AND resource_class IS NOT NULL AND usage_quantity IS NOT NULL AND usage_quantity >= 0 AND usage_unit IS NOT NULL)
    OR event_type!='RESOURCE_USAGE'
  ),
  CHECK(
    (event_type='FX_RATE_OBSERVED' AND currency IS NOT NULL AND fx_quote_currency IS NOT NULL AND fx_rate_text IS NOT NULL AND fx_rate_timestamp IS NOT NULL AND fx_rate_source IS NOT NULL)
    OR event_type!='FX_RATE_OBSERVED'
  ),
  CHECK(
    (event_type='REVERSAL' AND reversal_of_event_id IS NOT NULL)
    OR (event_type!='REVERSAL' AND reversal_of_event_id IS NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_economic_events_holding_time ON economic_events(holding_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_economic_events_trace ON economic_events(economic_trace_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_economic_events_type_time ON economic_events(event_type, observed_at);
CREATE INDEX IF NOT EXISTS idx_economic_events_parent_task ON economic_events(parent_task_id);

CREATE TRIGGER IF NOT EXISTS economic_events_no_update
BEFORE UPDATE ON economic_events
BEGIN
  SELECT RAISE(ABORT, 'E_ECON_LEDGER_APPEND_ONLY_UPDATE_FORBIDDEN');
END;

CREATE TRIGGER IF NOT EXISTS economic_events_no_delete
BEFORE DELETE ON economic_events
BEGIN
  SELECT RAISE(ABORT, 'E_ECON_LEDGER_APPEND_ONLY_DELETE_FORBIDDEN');
END;

CREATE VIEW IF NOT EXISTS economic_ledger_event_counts AS
SELECT event_type, holding_id, COUNT(*) AS event_count
FROM economic_events
GROUP BY event_type, holding_id;
CREATE VIEW IF NOT EXISTS economic_events_effective AS
SELECT e.* FROM economic_events e
WHERE e.event_type <> 'REVERSAL'
  AND NOT EXISTS (
    SELECT 1 FROM economic_events r
    WHERE r.event_type='REVERSAL' AND r.reversal_of_event_id=e.event_id
  );
