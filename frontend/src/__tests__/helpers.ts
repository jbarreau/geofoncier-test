/**
 * Build a fake JWT with a valid base64url-encoded payload.
 * The header and signature are stubs — only the payload matters for tests.
 */
export function makeFakeJwt(overrides: Record<string, unknown> = {}): string {
  const payload = {
    sub: 'user-1',
    email: 'test@example.com',
    roles: [],
    permissions: [] as string[],
    exp: 9999999999,
    ...overrides,
  }
  const encoded = btoa(JSON.stringify(payload))
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
  return `header.${encoded}.signature`
}

export const ADMIN_JWT = makeFakeJwt({ permissions: ['users:manage'] })
export const USER_JWT = makeFakeJwt({ permissions: [] })
