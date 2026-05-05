import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';

import ImageAds from './ImageAds';

vi.mock('../context/BrandContext', () => ({
  useBrands: () => ({
    activeBrand: {
      id: 'brand-1',
      name: 'Townsquare Interactive',
      voice: 'Helpful and direct',
      products: [
        {
          id: 'product-1',
          name: 'Digital Marketing',
          description: 'Local digital marketing services',
        },
      ],
    },
    customerProfiles: [],
  }),
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    authFetch: vi.fn(),
  }),
}));

vi.mock('../context/ToastContext', () => ({
  useToast: () => ({
    showError: vi.fn(),
  }),
}));

vi.mock('../components/StyleSelector', () => ({
  default: () => <div>Style selector</div>,
}));

vi.mock('../components/ImageTemplateSelector', () => ({
  default: () => <div>Template selector</div>,
}));

describe('ImageAds audience selection', () => {
  test('allows image ad creation with a general audience when no profiles exist', () => {
    render(<ImageAds />);

    expect(screen.getByText('General audience')).toBeInTheDocument();

    const continueButton = screen.getByRole('button', { name: /continue/i });
    expect(continueButton).toBeEnabled();

    fireEvent.click(continueButton);

    expect(screen.getByText('Select a Template or Style')).toBeInTheDocument();
  });
});
