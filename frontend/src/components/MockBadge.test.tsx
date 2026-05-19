import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { MockBadge } from './MockBadge';

describe('MockBadge', () => {
  afterEach(() => { cleanup(); });

  it('renders nothing for pipeline source', () => {
    const { container } = render(<MockBadge source="pipeline" />);
    expect(container.textContent).toBe('');
  });

  it('renders MOCK label for mock source', () => {
    render(<MockBadge source="mock" />);
    expect(screen.getByText('MOCK')).toBeDefined();
  });

  it('renders STUB label for stub source', () => {
    render(<MockBadge source="stub" />);
    expect(screen.getByText('STUB')).toBeDefined();
  });

  it('renders ? label for unknown source', () => {
    render(<MockBadge source="unknown" />);
    expect(screen.getByText('?')).toBeDefined();
  });

  it('renders nothing when source is undefined', () => {
    const { container } = render(<MockBadge source={undefined} />);
    expect(container.textContent).toBe('');
  });
});
