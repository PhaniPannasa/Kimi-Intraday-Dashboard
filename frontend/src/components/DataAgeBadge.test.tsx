import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DataAgeBadge } from './DataAgeBadge';

describe('DataAgeBadge', () => {
  it('should render nothing when timestamp is null', () => {
    const { container } = render(<DataAgeBadge timestamp={null} />);
    expect(container.textContent).toBe('');
  });

  it('should render relative age for a recent timestamp', () => {
    const recent = new Date(Date.now() - 5000).toISOString();
    render(<DataAgeBadge timestamp={recent} />);
    expect(screen.getByText(/Updated \d+s ago/)).toBeDefined();
  });
});
