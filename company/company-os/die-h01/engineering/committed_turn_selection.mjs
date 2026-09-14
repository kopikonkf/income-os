export const normalized=s=>String(s||'').replace(/\s+/g,' ').trim();

export function selectCommittedAnswer(turns,prompt){
  const matches=turns.map((t,i)=>t.role==='user'&&normalized(t.text)===normalized(prompt)?i:-1).filter(i=>i>=0);
  if(matches.length!==1)throw Error('E_COMMITTED_PROMPT_MATCH_COUNT:'+matches.length);
  const i=matches[0],answers=[];
  for(let n=i+1;n<turns.length&&turns[n].role!=='user';n++)if(turns[n].role==='assistant')answers.push(turns[n]);
  if(answers.length!==1)throw Error('E_COMMITTED_ASSISTANT_MATCH_COUNT:'+answers.length);
  const a=answers[0];
  if(a.thinking)throw Error('E_PROVIDER_STILL_THINKING');
  const candidates=[...new Set([...String(a.text||'').matchAll(/<svg\b[\s\S]*?<\/svg>/gi)].map(m=>m[0].trim()))];
  if(candidates.length!==1)throw Error('E_SCOPED_SVG_COUNT:'+candidates.length);
  return {svg:candidates[0],user_index:i,assistant_id:a.id||null,scope:'EXACT_NORMALIZED_USER_PROMPT_AND_FOLLOWING_ASSISTANT'};
}
