import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiFetch } from './apiFetch';

describe('apiFetch', () => {
  beforeEach(() => { vi.restoreAllMocks(); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('returns data and source=pipeline when header is pipeline', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'X-Data-Source': 'pipeline' }),
      json: async () => ({ value: 42 }),
    } as Response);

    const { data, source } = await apiFetch<{ value: number }>('/api/test');
    expect(data).toEqual({ value: 42 });
    expect(source).toBe('pipeline');
  });

  it('returns source=mock when header is mock', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'X-Data-Source': 'mock' }),
      json: async () => ([]),
    } as Response);
    const { source } = await apiFetch('/api/test');
    expect(source).toBe('mock');
  });

  it('defaults source to unknown when header is missing', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({}),
      json: async () => ({}),
    } as Response);
    const { source } = await apiFetch('/api/test');
    expect(source).toBe('unknown');
  });

  it('throws on non-200 responses', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 503,
      headers: new Headers({}),
      json: async () => ({}),
    } as Response);
    await expect(apiFetch('/api/test')).rejects.toThrow(/503/);
  });
});
