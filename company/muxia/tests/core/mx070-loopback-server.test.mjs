import test from 'node:test';
import assert from 'node:assert/strict';

import {
  createLegacyCompatibilityServer,
  MX070_LEGACY_HOST,
  MX070_LEGACY_PORT,
} from '../../dist/api/loopback-server.js';

test('MX-070: loopback facade exposes the legacy /v1/models doctor contract', async () => {
  let calls = 0;
  const facade = createLegacyCompatibilityServer({
    hostname: MX070_LEGACY_HOST,
    port: 0,
    executor: async () => {
      calls += 1;
      return { body: { ok: true } };
    },
  });
  const address = await facade.listen();
  try {
    const response = await fetch(`http://${address.hostname}:${address.port}/v1/models`);
    assert.equal(response.status, 200);
    const body = await response.json();
    assert.ok(Array.isArray(body.data));
    assert.ok(body.data.some((row) => row.id === 'chatgpt' && row.status === 'enabled'));
    assert.deepEqual(body.data[0].capabilities, ['image.generate']);
    assert.equal(body.compatibility.legacy_proxima_process, false);
    assert.equal(body.compatibility.authority_expanded, false);
    assert.equal(calls, 0);
  } finally {
    await facade.close();
  }
});

test('MX-070: chat/completions preserves bounded request body for injected MUXIA executor', async () => {
  const seen = [];
  const facade = createLegacyCompatibilityServer({
    hostname: '127.0.0.1',
    port: 0,
    executor: async (request) => {
      seen.push(request);
      return {
        body: {
          id: 'mx070-test',
          object: 'chat.completion',
          muxia_job_id: 'job-001',
          artifact_receipt: { sha256: 'a'.repeat(64), status: 'VERIFIED' },
        },
      };
    },
  });
  const address = await facade.listen();
  try {
    const request = {
      model: 'chatgpt',
      messages: [{ role: 'user', content: 'bounded legacy payload' }],
      temperature: 0,
      muxia_compat: { task_id: 'M001J2A1' },
    };
    const response = await fetch(`http://${address.hostname}:${address.port}/v1/chat/completions`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(request),
    });
    assert.equal(response.status, 200);
    const body = await response.json();
    assert.equal(body.muxia_job_id, 'job-001');
    assert.deepEqual(seen, [request]);
  } finally {
    await facade.close();
  }
});

test('MX-070: facade fails closed on non-chatgpt model, streaming, unknown routes and non-loopback bind', async () => {
  assert.equal(MX070_LEGACY_PORT, 3211);
  assert.throws(() => createLegacyCompatibilityServer({ hostname: '0.0.0.0', executor: async () => ({ body: {} }) }), /MX070_LOOPBACK_HOST_REQUIRED/);

  const facade = createLegacyCompatibilityServer({ hostname: '127.0.0.1', port: 0, executor: async () => ({ body: { ok: true } }) });
  const address = await facade.listen();
  try {
    let response = await fetch(`http://${address.hostname}:${address.port}/v1/chat/completions`, {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ model: 'paid-or-other-model' }),
    });
    assert.equal(response.status, 400);
    assert.equal((await response.json()).error.code, 'LEGACY_MODEL_NOT_ALLOWED');

    response = await fetch(`http://${address.hostname}:${address.port}/v1/chat/completions`, {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ model: 'chatgpt', stream: true }),
    });
    assert.equal(response.status, 400);
    assert.equal((await response.json()).error.code, 'LEGACY_STREAMING_NOT_SUPPORTED');

    response = await fetch(`http://${address.hostname}:${address.port}/not-a-route`);
    assert.equal(response.status, 404);
  } finally {
    await facade.close();
  }
});
