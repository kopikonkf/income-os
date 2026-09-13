export const bridgePolicy={browser_native_primary:true,browser_native_replacement_allowed:false,capacity_mode:'OPPORTUNISTIC_SUPPLEMENTAL_ONLY',scheduling_authority:'MISSION_CONTROL',direct_routing_authority:false,secret_values_exposed:false,production_role_default:'DISABLED'};

export const ROLE='H01_SVG_GENERATION';
const KINDS=new Set(['OPENAI_COMPATIBLE','ANTHROPIC_API','GEMINI_API','CUSTOM_API']);
const STATES=new Set(['UNCONFIGURED','CONFIGURED','DISABLED']);
const HEALTH=new Set(['UNKNOWN','HEALTHY','DEGRADED','UNHEALTHY']);
const CAPS=new Set(['TEXT','TEXT_SVG','NATIVE_SVG','RASTER_IMAGE']);

export function normalizeProvider(input){ const p={provider_id:String(input.provider_id||''),display_name:String(input.display_name||''),provider_kind:String(input.provider_kind||''),api_base_origin:String(input.api_base_origin||''),connection_state:String(input.connection_state||'UNCONFIGURED'),credential_reference_present:Boolean(input.credential_reference_present),health:{status:String(input.health?.status||'UNKNOWN'),observed_at:input.health?.observed_at||null},capabilities:[...new Set(input.capabilities||[])].sort(),production_roles:{[ROLE]:String(input.production_roles?.[ROLE]||'DISABLED')}}; if(!p.provider_id||!p.display_name)throw new Error('E_PROVIDER_IDENTITY'); if(!KINDS.has(p.provider_kind))throw new Error('E_PROVIDER_KIND'); if(!STATES.has(p.connection_state))throw new Error('E_CONNECTION_STATE'); if(!HEALTH.has(p.health.status))throw new Error('E_HEALTH_STATUS'); if(p.capabilities.some(x=>!CAPS.has(x)))throw new Error('E_CAPABILITY'); if(!['ENABLED','DISABLED'].includes(p.production_roles[ROLE]))throw new Error('E_PRODUCTION_ROLE'); return p }

export function isSupplementalEligible(input,role=ROLE){const p=normalizeProvider(input); const svg=p.capabilities.includes('NATIVE_SVG')||p.capabilities.includes('TEXT_SVG'); return role===ROLE&&p.production_roles[ROLE]==='ENABLED'&&p.connection_state==='CONFIGURED'&&p.credential_reference_present&&p.health.status==='HEALTHY'&&svg}
export function buildProviderBridgeReadModel(runtime={providers:[]}){const providers=(runtime.providers||[]).map(normalizeProvider); return {policy:bridgePolicy,provider_count:providers.length,eligible_supplemental_provider_ids:providers.filter(p=>isSupplementalEligible(p)).map(p=>p.provider_id),providers}}
export const DEFAULT_RUNTIME=Object.freeze({providers:[]});
