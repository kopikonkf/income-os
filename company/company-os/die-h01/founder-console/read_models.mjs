import {readdir, readFile, stat} from 'node:fs/promises';
import net from 'node:net';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {buildProviderBridgeReadModel, DEFAULT_RUNTIME} from './byok_bridge.mjs';

const ROOT=path.dirname(fileURLToPath(import.meta.url));
const DEFAULTS=Object.freeze({
  runRoot:'/var/lib/die/h01/runs',
  h01_108_root:'/var/lib/die/h01/runs/H01-108',
  submissionReadyRoot:'/var/lib/die/h01/submission-ready',
  graphPath:path.join(ROOT,'..','die-h01-task-graph.v1.json'),
  legacyHost:'127.0.0.1', legacyPort:8876
});

async function entries(p){try{return await readdir(p,{withFileTypes:true})}catch{return []}}
async function exists(p){try{await stat(p);return true}catch{return false}}
async function countNamed(root,name,maxDepth=3,depth=0){let n=0;for(const e of await entries(root)){const p=path.join(root,e.name);if(e.isFile()&&e.name===name)n++;else if(e.isDirectory()&&depth<maxDepth)n+=await countNamed(p,name,maxDepth,depth+1)}return n}
async function graph(pathname){try{return JSON.parse(await readFile(pathname,'utf8'))}catch{return {tasks:[]}}}
function summarizeGraph(g){const counts={};for(const t of g.tasks||[])counts[t.status]=(counts[t.status]||0)+1;return {task_count:(g.tasks||[]).length,status_counts:counts,ready_ids:(g.tasks||[]).filter(t=>t.status==='READY').map(t=>t.id).slice(0,25)}}
function portOpen(host,port,timeout=350){return new Promise(resolve=>{const s=net.createConnection({host,port});const done=v=>{s.destroy();resolve(v)};s.setTimeout(timeout);s.once('connect',()=>done(true));s.once('timeout',()=>done(false));s.once('error',()=>done(false))})}

export function createReadModels(options={}){
  const cfg={...DEFAULTS,...options};
  return {
    async overview(){const g=summarizeGraph(await graph(cfg.graphPath));return {mission_control:'GLOBAL_BRAIN',h01_runtime:'EXECUTION_PLANE',console_mode:'SHADOW_READ_ONLY_V1',legacy_8876:await portOpen(cfg.legacyHost,cfg.legacyPort)?'LISTENING':'UNAVAILABLE',task_count:g.task_count,ready_tasks:g.ready_ids.length}},
    async production(){const dirs=(await entries(cfg.runRoot)).filter(e=>e.isDirectory());return {lane:'VECTOR',mode:'VECTOR_OBJECT',form:'SINGLE',preset:'CLEAN_STOCK_VECTOR_V1',run_groups:dirs.length,recent_run_groups:dirs.map(e=>e.name).sort().slice(-10).reverse(),mutation:false}},
    async providers(){return {browser_native_primary:true,credential_values_exposed:false,api_bridge:buildProviderBridgeReadModel(DEFAULT_RUNTIME)}},
    async qcGallery(){return {gallery:'read-only',preview_count:await countNamed(cfg.h01_108_root,'preview.webp'),legacy_url:'http://127.0.0.1:8876/#qc',legacy_8876:await portOpen(cfg.legacyHost,cfg.legacyPort)?'LISTENING':'UNAVAILABLE',founder_qc_authority:'FOUNDER'}},
    async submissionReady(){const rows=(await entries(cfg.submissionReadyRoot)).filter(e=>e.isDirectory()||e.isFile());return {root:cfg.submissionReadyRoot,root_exists:await exists(cfg.submissionReadyRoot),entry_count:rows.length,submission_action:'NONE',publication_action:'NONE'}},
    async demand(){const g=await graph(cfg.graphPath);const ids=new Set(['H01-130','H01-131','H01-132','H01-133']);return {engines:(g.tasks||[]).filter(t=>ids.has(t.id)).map(t=>({id:t.id,status:t.status,title:t.title,result:t.result||null})),queue_mutation:false}},
    async tasks(){return {scheduler:'MISSION_CONTROL',graph_authority:'MISSION_CONTROL',local_canonical_snapshot:summarizeGraph(await graph(cfg.graphPath)),lease_mutation:false}},
    async systemHealth(){return {console:'PASS',adapter:'PASS',upstream_9router_pin:'0.5.75',legacy_8876:await portOpen(cfg.legacyHost,cfg.legacyPort)?'LISTENING':'UNAVAILABLE',h01_run_root_exists:await exists(cfg.runRoot)}},
    async settings(){return {secret_values_exposed:false,mutation:false,upstream_mode:'UI_SHELL_ONLY',run_root:cfg.runRoot,submission_ready_root:cfg.submissionReadyRoot,legacy_8876_port:cfg.legacyPort}}
  };
}

export const DEFAULT_READ_MODELS=createReadModels();
