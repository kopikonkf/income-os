#!/usr/bin/env node
import path from 'node:path';
import { runRoundtrip } from './cognition_roundtrip_core.mjs';
const requestFile=process.argv[2] ? path.resolve(process.argv[2]) : null; const responseFile=process.argv[3] ? path.resolve(process.argv[3]) : null;
if(!requestFile){console.error('usage: cognition_roundtrip.mjs REQUEST_JSON [RESPONSE_TEXT]');process.exit(2);}
try{console.log(JSON.stringify(await runRoundtrip({requestFile,responseFile})));process.exit(0);}catch(e){console.error(e instanceof Error?e.message:String(e));process.exit(2);}
