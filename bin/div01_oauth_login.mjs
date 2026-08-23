#!/usr/bin/env node
// Division-01 ChatGPT OAuth PKCE login (bootstrap only; runtime wake does NOT use this).
// Proven flow per D:\OAUTH\docs\raw\chatgpt-oauth-openai-compatible.md
// Usage: node div01_oauth_login.mjs [--code-home <dir>] (default C:\Users\aethers\.codex-DIVISION-01)

import http from "node:http";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { execFile } from "node:child_process";

const CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann";
const REDIRECT_URI = "http://localhost:1455/auth/callback";
const AUTH_URL = "https://auth.openai.com/oauth/authorize";
const TOKEN_URL = "https://auth.openai.com/oauth/token";
const BRAVE = "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe";
const BRAVE_PROFILE = "Profile 3"; // "plus"

const args = process.argv.slice(2);
const codeHomeIdx = args.indexOf("--code-home");
const CODE_HOME = codeHomeIdx >= 0 ? args[codeHomeIdx + 1] : path.join(process.env.USERPROFILE, ".codex-DIVISION-01");

const b64url = (buf) => Buffer.from(buf).toString("base64url");
const verifier = b64url(crypto.randomBytes(48));
const challenge = b64url(crypto.createHash("sha256").update(verifier).digest());
const state = b64url(crypto.randomBytes(24));

const url =
  `${AUTH_URL}?response_type=code&client_id=${CLIENT_ID}` +
  `&redirect_uri=${encodeURIComponent(REDIRECT_URI)}` +
  `&scope=openid+profile+email+offline_access&state=${state}` +
  `&code_challenge=${challenge}&code_challenge_method=S256` +
  `&id_token_add_organizations=true&codex_cli_simplified_flow=true`;

function jwtPayload(tok) {
  try {
    const p = tok.split(".")[1];
    return JSON.parse(Buffer.from(p, "base64").toString("utf8"));
  } catch {
    return {};
  }
}

async function exchange(code) {
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: REDIRECT_URI,
    client_id: CLIENT_ID,
    code_verifier: verifier,
  });
  const res = await fetch(TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error(`token exchange ${res.status}: ${await res.text()}`);
  return res.json();
}

const server = http.createServer(async (req, res) => {
  const u = new URL(req.url, REDIRECT_URI);
  if (u.pathname !== "/auth/callback") {
    res.writeHead(404).end();
    return;
  }
  if (u.searchParams.get("state") !== state) {
    res.writeHead(400, { "Content-Type": "text/plain" }).end("state mismatch");
    console.error("E_STATE_MISMATCH");
    process.exit(2);
  }
  const code = u.searchParams.get("code");
  if (!code) {
    res.writeHead(400, { "Content-Type": "text/plain" }).end("missing code");
    console.error("E_NO_CODE");
    process.exit(2);
  }
  res.writeHead(200, { "Content-Type": "text/html" }).end("<html><body><h3>DIVISION-01 login OK. Tab ini boleh ditutup.</h3></body></html>");
  try {
    const tok = await exchange(code);
    fs.mkdirSync(CODE_HOME, { recursive: true });
    const authJson = {
      auth_mode: "chatgpt",
      tokens: {
        id_token: tok.id_token || null,
        access_token: tok.access_token,
        refresh_token: tok.refresh_token || null,
        account_id: jwtPayload(tok.id_token || tok.access_token)["https://api.openai.com/auth"].account_id || null,
      },
      last_refresh: new Date().toISOString(),
    };
    fs.writeFileSync(path.join(CODE_HOME, "auth.json"), JSON.stringify(authJson, null, 2), { encoding: "utf8" });
    console.log("LOGIN_OK");
    console.log(`auth.json written to ${path.join(CODE_HOME, "auth.json")}`);
    const claims = jwtPayload(tok.access_token);
    console.log(`access_token exp=${claims.exp ? new Date(claims.exp * 1000).toISOString() : "unknown"} plan=${(claims["https://api.openai.com/auth"] || {}).chatgpt_plan_type || "unknown"}`);
  } catch (e) {
    console.error("E_EXCHANGE", e.message);
    process.exit(3);
  }
  server.close();
  process.exit(0);
});

server.listen(1455, "127.0.0.1", () => {
  console.log("PKCE server listening on 127.0.0.1:1455");
  console.log("AUTH_URL:");
  console.log(url);
  execFile(BRAVE, [`--profile-directory=${BRAVE_PROFILE}`, url], (err) => {
    if (err) console.error("E_BRAVE_OPEN (buka URL manual di Brave profil plus):", err.message);
  });
});
