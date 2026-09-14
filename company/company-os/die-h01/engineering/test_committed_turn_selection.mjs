import test from 'node:test';import assert from 'node:assert/strict';
import {selectCommittedAnswer} from './committed_turn_selection.mjs';
const svg=n=>`<svg viewBox="0 0 10 10"><rect width="${n}" height="${n}"/></svg>`;
test('selects only exact prompt following assistant',()=>{const r=selectCommittedAnswer([{role:'user',text:'make houseplant'},{role:'assistant',text:svg(5),id:'a1'}],'make   houseplant');assert.equal(r.svg,svg(5));assert.equal(r.assistant_id,'a1')});
test('never takes svg from later turn',()=>{assert.throws(()=>selectCommittedAnswer([{role:'user',text:'houseplant'},{role:'assistant',text:'PNG image only',id:'a1'},{role:'user',text:'candy cane'},{role:'assistant',text:svg(7),id:'a2'}],'houseplant'),/E_SCOPED_SVG_COUNT:0/)});
test('thinking is not terminal',()=>{assert.throws(()=>selectCommittedAnswer([{role:'user',text:'x'},{role:'assistant',text:svg(2),thinking:true}],'x'),/E_PROVIDER_STILL_THINKING/)});
test('ambiguous duplicate prompt fails',()=>{assert.throws(()=>selectCommittedAnswer([{role:'user',text:'x'},{role:'assistant',text:svg(2)},{role:'user',text:'x'},{role:'assistant',text:svg(3)}],'x'),/E_COMMITTED_PROMPT_MATCH_COUNT:2/)});
test('multiple assistant answers fail',()=>{assert.throws(()=>selectCommittedAnswer([{role:'user',text:'x'},{role:'assistant',text:'thinking done'},{role:'assistant',text:svg(3)}],'x'),/E_COMMITTED_ASSISTANT_MATCH_COUNT:2/)});
test('multiple svg payloads fail',()=>{assert.throws(()=>selectCommittedAnswer([{role:'user',text:'x'},{role:'assistant',text:svg(2)+svg(3)}],'x'),/E_SCOPED_SVG_COUNT:2/)});
