from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'company'/'muxia'/'receipts'/'MCP-LNX-003-chatgpt-tool-scan.acceptance.receipt.json'
def test_mcp_lnx003_real_chatgpt_tool_catalog_is_6_18_and_task_remains_open_for_context_call():
    d=json.loads(R.read_text(encoding='utf-8'))
    assert d['chatgpt_cloud_scan']['division01']['observed_tool_count']==6
    assert d['chatgpt_cloud_scan']['division01']['result']=='PASS'
    assert d['chatgpt_cloud_scan']['executive']['observed_tool_count']==18
    assert d['chatgpt_cloud_scan']['executive']['result']=='PASS'
    assert d['runtime']['version']=='1.3.0'
    assert d['task_status_after_receipt']=='READY'
    graph=json.loads((ROOT/'company'/'muxia-task-graph-v1.json').read_text(encoding='utf-8'))
    task=next(x for x in graph['tasks'] if x['id']=='MCP-LNX-003')
    assert task['status']=='READY'
