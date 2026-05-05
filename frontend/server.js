import express from 'express';
import { existsSync } from 'node:fs';
import { dirname, extname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const distDir = join(__dirname, 'dist');
const port = process.env.PORT || 3000;

export const createFrontendApp = ({ distDir: appDistDir = distDir } = {}) => {
  const indexPath = join(appDistDir, 'index.html');

  if (!existsSync(indexPath)) {
    throw new Error(`Missing frontend build at ${indexPath}. Run npm run build before starting the server.`);
  }

  const app = express();

  app.disable('x-powered-by');
  app.use(express.static(appDistDir));

  app.use((req, res, next) => {
    if (req.method !== 'GET' || !req.accepts('html') || extname(req.path)) {
      next();
      return;
    }

    res.sendFile(indexPath);
  });

  return app;
};

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try {
    const app = createFrontendApp();

    app.listen(port, '0.0.0.0', () => {
      console.log(`Frontend server listening on port ${port}`);
    });
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}
