import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

describe('Railway frontend config', () => {
  test('starts the explicit frontend server on Railway', () => {
    const railwayConfig = readFileSync(join(process.cwd(), 'railway.toml'), 'utf8');

    expect(railwayConfig).toMatch(/node server\.js/);
    expect(existsSync(join(process.cwd(), 'server.js'))).toBe(true);
  });

  test('frontend server falls back HTML client routes to index.html', () => {
    const server = readFileSync(join(process.cwd(), 'server.js'), 'utf8');

    expect(server).toContain('express.static(appDistDir)');
    expect(server).toContain("req.accepts('html')");
    expect(server).toContain('extname(req.path)');
    expect(server).toContain('res.sendFile(indexPath)');
  });
});
