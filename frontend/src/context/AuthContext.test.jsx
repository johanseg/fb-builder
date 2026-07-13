import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { AuthProvider, useAuth } from './AuthContext';

function RefreshHarness() {
  const { refreshAccessToken } = useAuth();

  return <button onClick={() => refreshAccessToken()}>refresh</button>;
}

describe('AuthContext refresh flow', () => {
  test('refreshAccessToken fetches the user with the refreshed token', async () => {
    localStorage.getItem.mockImplementation((key) => {
      if (key === 'refreshToken') {
        return 'stale-refresh-token';
      }
      return null;
    });

    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'fresh-access-token',
          refresh_token: 'fresh-refresh-token',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 'user-1',
          email: 'test@example.com',
          roles: [],
        }),
      });

    render(
      <AuthProvider>
        <RefreshHarness />
      </AuthProvider>
    );

    fireEvent.click(screen.getByText('refresh'));

    await waitFor(() => {
      expect(fetch).toHaveBeenNthCalledWith(
        2,
        expect.stringContaining('/auth/me'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer fresh-access-token',
          }),
        })
      );
    });
  });
});
