import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import http from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, describe, expect, test } from 'vitest';

import { createFrontendApp } from '../../server.js';

const servers = [];
const tempDirs = [];

const listen = (app) => new Promise((resolve) => {
  const server = app.listen(0, '127.0.0.1', () => {
    servers.push(server);
    resolve(server);
  });
});

const urlFor = (server, path) => {
  const { port } = server.address();
  return `http://127.0.0.1:${port}${path}`;
};

const request = (url, headers = {}) => new Promise((resolve, reject) => {
  http.get(url, { headers }, (response) => {
    let body = '';

    response.setEncoding('utf8');
    response.on('data', (chunk) => {
      body += chunk;
    });
    response.on('end', () => {
      resolve({
        body,
        headers: response.headers,
        status: response.statusCode,
      });
    });
  }).on('error', reject);
});

const createDist = () => {
  const distDir = mkdtempSync(join(tmpdir(), 'frontend-dist-'));
  tempDirs.push(distDir);
  mkdirSync(join(distDir, 'assets'));
  writeFileSync(join(distDir, 'index.html'), '<main>SPA shell</main>');
  writeFileSync(join(distDir, 'assets', 'app.js'), 'console.log("app");');
  return distDir;
};

afterEach(async () => {
  await Promise.all(servers.splice(0).map(
    (server) => new Promise((resolve) => server.close(resolve))
  ));

  tempDirs.splice(0).forEach((dir) => {
    rmSync(dir, { recursive: true, force: true });
  });
});

describe('frontend production server', () => {
  test('falls back client routes to the SPA shell', async () => {
    const app = createFrontendApp({ distDir: createDist() });
    const server = await listen(app);

    const response = await request(urlFor(server, '/image-ads'), {
      Accept: 'text/html',
    });

    expect(response.status).toBe(200);
    expect(response.headers['content-type']).toContain('text/html');
    expect(response.body).toContain('SPA shell');
  });

  test('does not return index.html for missing asset paths', async () => {
    const app = createFrontendApp({ distDir: createDist() });
    const server = await listen(app);

    const response = await request(urlFor(server, '/assets/missing.js'), {
      Accept: '*/*',
    });

    expect(response.status).toBe(404);
    expect(response.body).not.toContain('SPA shell');
  });
});
