import { spawnSync } from 'node:child_process';

const audit = spawnSync('npm', ['audit', '--omit=dev', '--json'], { encoding: 'utf8' });
const report = JSON.parse(audit.stdout);
const vulnerabilities = report.vulnerabilities || {};
const routerAdvisory = vulnerabilities['react-router']?.via?.some(
  (item) => item?.url === 'https://github.com/advisories/GHSA-qwww-vcr4-c8h2',
);
const onlyKnownSpaException = routerAdvisory
  && Object.keys(vulnerabilities).every((name) => ['react-router', 'react-router-dom'].includes(name))
  && report.metadata?.vulnerabilities?.high === 2
  && report.metadata?.vulnerabilities?.critical === 0;

if (audit.status && !onlyKnownSpaException) {
  process.stderr.write(audit.stdout || audit.stderr);
  process.exit(audit.status);
}

if (onlyKnownSpaException) {
  console.warn('Accepted GHSA-qwww-vcr4-c8h2: this Vite SPA uses no React Router RSC/server actions; fail on any other production advisory.');
}
