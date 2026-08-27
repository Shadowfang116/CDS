const baseUrl = process.env.FRONTEND_URL || 'http://localhost:3100';

const routes = [
  '/', '/login', '/change-password', '/dashboard', '/dashboard/cases',
  '/dashboard/documents', '/dashboard/exceptions', '/dashboard/cp',
  '/dashboard/evaluations', '/dashboard/settings', '/dashboard/audit',
  '/approvals', '/admin', '/analytics', '/cases/demo', '/digests',
  '/governance', '/inbox', '/integrations', '/matters/demo', '/reports',
  '/tutorial',
];

let failures = 0;

for (const route of routes) {
  const response = await fetch(`${baseUrl}${route}`, { redirect: 'manual' });
  if (response.status < 200 || response.status >= 400) {
    failures += 1;
    console.error(`[FAIL] ${route} -> ${response.status}`);
  } else {
    console.log(`[OK] ${route} -> ${response.status}`);
  }
}

if (failures > 0) {
  process.exitCode = 1;
}
