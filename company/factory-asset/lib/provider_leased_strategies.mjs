import * as chatgpt from '../providers/chatgpt/linux/chatgpt_leased_strategy.mjs';
import * as gemini from '../providers/gemini/linux/gemini_leased_strategy.mjs';
import * as manus from '../providers/manus/linux/manus_leased_strategy.mjs';
import * as duckai from '../providers/duckai/linux/duckai_leased_strategy.mjs';
const STRATEGIES={chatgpt,gemini,manus,duckai};
export function providerSettleMs(providerId){return STRATEGIES[providerId]?.settleMs??2200;}
export function hasLeasedStrategy(providerId){return Boolean(STRATEGIES[providerId]);}
export async function prepareLeasedStrategy(providerId,args){const s=STRATEGIES[providerId];if(!s)throw new Error(`E_PROVIDER_STRATEGY_UNAVAILABLE:${providerId}`);return await s.prepare(args);}
export async function submitLeasedStrategy(providerId,args){const s=STRATEGIES[providerId];if(!s)throw new Error(`E_PROVIDER_STRATEGY_UNAVAILABLE:${providerId}`);return await s.submit(args);}
export async function waitLeasedStrategy(providerId,args){const s=STRATEGIES[providerId];if(!s)throw new Error(`E_PROVIDER_STRATEGY_UNAVAILABLE:${providerId}`);return await s.waitForOutput(args);}
export async function cleanupLeasedStrategy(providerId,args){const s=STRATEGIES[providerId];if(s?.cleanup)await s.cleanup(args);}
