import React from 'react';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import Reporting from './Reporting';

const mocks = vi.hoisted(() => ({
  canSync: false,
  authFetch: vi.fn(),
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    authFetch: mocks.authFetch,
    hasPermission: (permission) => permission === 'reporting:sync' && mocks.canSync,
  }),
}));

vi.mock('../context/BrandContext', () => ({
  useBrands: () => ({ activeBrand: { id: 'brand-1', name: 'Reporting brand' } }),
}));

vi.mock('../context/ToastContext', () => ({
  useToast: () => ({ showError: vi.fn() }),
}));

const report = {
  partial: false,
  summaries: [],
  recommendations: [],
};

describe('Reporting permissions', () => {
  beforeEach(() => {
    mocks.canSync = false;
    mocks.authFetch.mockResolvedValue({ ok: true, json: async () => report });
  });

  test('hides the Meta sync control without reporting:sync', async () => {
    render(<Reporting />);

    await screen.findByText('Read-only recommendations');
    expect(screen.queryByRole('button', { name: /sync meta data/i })).not.toBeInTheDocument();
  });

  test('shows the Meta sync control with reporting:sync', async () => {
    mocks.canSync = true;
    render(<Reporting />);

    await screen.findByText('Read-only recommendations');
    expect(screen.getByRole('button', { name: /sync meta data/i })).toBeInTheDocument();
  });
});
