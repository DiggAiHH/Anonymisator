import request from 'supertest';
import { createApp } from '../src/index';

describe('MCP Tool Server (deterministic)', () => {
  const originalEnv = { ...process.env };
  let logSpy: ReturnType<typeof jest.spyOn> | undefined;

  beforeAll(() => {
    logSpy = jest.spyOn(console, 'log').mockImplementation(() => undefined);
  });

  afterAll(() => {
    logSpy?.mockRestore();
    process.env = originalEnv;
  });

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  test('GET /health returns healthy with deterministic timestamp', async () => {
    const fixedMs = 1_700_000_000_000;
    const app = createApp({ clock: () => fixedMs });

    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body.status).toBe('healthy');
    expect(res.body.service).toBe('MCP Tool Server');
    expect(res.body.timestamp).toBe(new Date(fixedMs).toISOString());
  });

  test('GET /tools/get_free_slots fails closed with 503 when auth misconfigured', async () => {
    process.env.MCP_REQUIRE_API_KEY = 'true';
    process.env.MCP_API_KEY = '';
    process.env.MCP_RATE_LIMIT_ENABLED = 'false';

    const fixedMs = 1_700_000_000_000;
    const app = createApp({ clock: () => fixedMs });

    const res = await request(app).get('/tools/get_free_slots');
    expect(res.status).toBe(503);
    expect(res.body.error).toBe('Auth misconfigured');
  });

  test('GET /tools/get_free_slots returns 401 when missing/invalid key', async () => {
    process.env.MCP_REQUIRE_API_KEY = 'true';
    process.env.MCP_API_KEY = 'expected';
    process.env.MCP_RATE_LIMIT_ENABLED = 'false';

    const app = createApp({ clock: () => 1_700_000_000_000 });

    const res = await request(app).get('/tools/get_free_slots');
    expect(res.status).toBe(401);
    expect(res.body.error).toBe('Unauthorized');
  });

  test('GET /tools/get_free_slots allows missing key when auth disabled', async () => {
    process.env.MCP_REQUIRE_API_KEY = 'false';
    process.env.MCP_API_KEY = '';
    process.env.MCP_RATE_LIMIT_ENABLED = 'false';

    const fixedMs = 1_700_000_000_000;
    const app = createApp({ clock: () => fixedMs });

    const res = await request(app).get('/tools/get_free_slots');
    expect(res.status).toBe(200);
    expect(res.body.date).toBe(new Date(fixedMs).toISOString().split('T')[0]);
    expect(Array.isArray(res.body.slots)).toBe(true);
  });

  test('GET /tools/get_free_slots validates date format (400) after auth passes', async () => {
    process.env.MCP_REQUIRE_API_KEY = 'true';
    process.env.MCP_API_KEY = 'expected';
    process.env.MCP_RATE_LIMIT_ENABLED = 'false';

    const fixedMs = 1_700_000_000_000;
    const app = createApp({ clock: () => fixedMs });

    const res = await request(app)
      .get('/tools/get_free_slots')
      .set('X-API-Key', 'expected')
      .query({ date: '01-02-2025' });

    expect(res.status).toBe(400);
    expect(res.body.error).toContain('Invalid date format');
  });

  test('Rate limit returns 429 with Retry-After on second immediate call', async () => {
    process.env.MCP_REQUIRE_API_KEY = 'true';
    process.env.MCP_API_KEY = 'expected';
    process.env.MCP_RATE_LIMIT_ENABLED = 'true';
    process.env.MCP_RATE_LIMIT_RPS = '100';
    process.env.MCP_RATE_LIMIT_BURST = '1';

    let nowMs = 1_700_000_000_000;
    const clock = () => nowMs;
    const app = createApp({ clock });

    const r1 = await request(app)
      .get('/tools/get_free_slots')
      .set('X-API-Key', 'expected');
    expect(r1.status).toBe(200);

    const r2 = await request(app)
      .get('/tools/get_free_slots')
      .set('X-API-Key', 'expected');
    expect(r2.status).toBe(429);
    expect(r2.headers['retry-after']).toBeDefined();

    // After advancing time enough, request should pass again.
    nowMs += 1000;
    const r3 = await request(app)
      .get('/tools/get_free_slots')
      .set('X-API-Key', 'expected');
    expect(r3.status).toBe(200);
  });

  test('Retry-After is numeric and clock-deterministic (golden path)', async () => {
    process.env.MCP_REQUIRE_API_KEY = 'true';
    process.env.MCP_API_KEY = 'expected';
    process.env.MCP_RATE_LIMIT_ENABLED = 'true';
    process.env.MCP_RATE_LIMIT_RPS = '0.5';
    process.env.MCP_RATE_LIMIT_BURST = '1';

    let nowMs = 1_700_000_000_000;
    const clock = () => nowMs;
    const app = createApp({ clock });

    const ok1 = await request(app)
      .get('/tools/get_free_slots')
      .set('X-API-Key', 'expected');
    expect(ok1.status).toBe(200);

    const limited1 = await request(app)
      .get('/tools/get_free_slots')
      .set('X-API-Key', 'expected');
    expect(limited1.status).toBe(429);

    const retryAfter1 = limited1.headers['retry-after'];
    expect(retryAfter1).toBe('2');
    expect(Number.isFinite(Number(retryAfter1))).toBe(true);
    expect(Number.isInteger(Number(retryAfter1))).toBe(true);
    expect(Number(retryAfter1)).toBeGreaterThanOrEqual(1);

    nowMs += 1000;
    const limited2 = await request(app)
      .get('/tools/get_free_slots')
      .set('X-API-Key', 'expected');
    expect(limited2.status).toBe(429);

    const retryAfter2 = limited2.headers['retry-after'];
    expect(retryAfter2).toBe('1');
    expect(Number.isFinite(Number(retryAfter2))).toBe(true);
    expect(Number.isInteger(Number(retryAfter2))).toBe(true);
    expect(Number(retryAfter2)).toBeGreaterThanOrEqual(1);

    nowMs += 1000;
    const ok2 = await request(app)
      .get('/tools/get_free_slots')
      .set('X-API-Key', 'expected');
    expect(ok2.status).toBe(200);
  });
});
