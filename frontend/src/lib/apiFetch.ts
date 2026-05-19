export type DataSource = 'pipeline' | 'mock' | 'stub' | 'unknown';

export interface ApiFetchResult<T> {
  data: T;
  source: DataSource;
}

export async function apiFetch<T>(url: string, init?: RequestInit): Promise<ApiFetchResult<T>> {
  const res = init ? await fetch(url, init) : await fetch(url);
  if (!res.ok) {
    throw new Error(`apiFetch(${url}) → HTTP ${res.status}`);
  }
  const sourceHeader = res.headers.get('X-Data-Source') ?? res.headers.get('x-data-source');
  const source: DataSource =
    sourceHeader === 'pipeline' || sourceHeader === 'mock' || sourceHeader === 'stub'
      ? sourceHeader
      : 'unknown';
  const data = (await res.json()) as T;
  return { data, source };
}
