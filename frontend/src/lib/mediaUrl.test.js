import { resolveMediaUrl } from './mediaUrl';

test('resolves backend upload paths against the API origin', () => {
  const resolved = resolveMediaUrl(
    '/uploads/generated_123.png',
    'https://fb-builder-production.up.railway.app/api/v1',
  );

  expect(resolved).toBe('https://fb-builder-production.up.railway.app/uploads/generated_123.png');
});

test('leaves external media URLs unchanged', () => {
  const externalUrl = 'https://fal.media/generated.png';

  expect(resolveMediaUrl(externalUrl)).toBe(externalUrl);
});
