import fs from 'node:fs';
import { chromium } from 'playwright';
import { detectChatGptPageState, CHATGPT_STATE_DETECTOR_VERSION } from '../dist/providers/chatgpt/state-detector.js';

const sessionPath = process.env.MUXIA_EDGE_SESSION_VERIFY ?? 'C:\\DIE\\workspaces\\MUXIA-B04\\muxia-root\\state\\mx032-edge-session-verify.json';
const raw = fs.readFileSync(sessionPath, 'utf8').replace(/^\uFEFF/, '');
const session = JSON.parse(raw);
const debugUrl = `http://${session.debug_host}:${session.debug_port}`;

const browser = await chromium.connectOverCDP(debugUrl, { timeout: 5000 });
const context = browser.contexts()[0];
const pages = context.pages();
const page = pages.find((p) => /chatgpt\.com/i.test(p.url())) ?? pages[0];
if (!page) throw new Error('NO_CHATGPT_PAGE');

const observation = await detectChatGptPageState(page, new Date().toISOString());
console.log(JSON.stringify({
  schema: 'die.muxia.mx032.edge-sanitized-state-check.v1',
  detector_version: CHATGPT_STATE_DETECTOR_VERSION,
  profile_id: session.profile_id,
  state: observation.state,
  reason: observation.reason,
  signals: observation.signals,
  url: observation.url,
  operator_action_required: observation.operatorActionRequired,
  credential_values_read: false,
  prompt_submitted: false,
  output_extracted: false
}, null, 2));

process.exit(0);
