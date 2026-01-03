/**
 * Minimal MCP Tool Server for SecureDoc Flow
 * 
 * Improvements:
 * - Enhanced error handling middleware
 * - Request logging for observability
 * - Graceful shutdown handling
 * - Input sanitization and validation
 * - Better TypeScript type safety
 */

import express, { Request, Response, NextFunction, RequestHandler } from 'express';
import crypto from 'crypto';

type Clock = () => number; // milliseconds

interface AppOptions {
  clock?: Clock;
}

function envBool(name: string, defaultValue: boolean): boolean {
  const raw = process.env[name];
  if (raw == null) return defaultValue;
  const v = raw.trim().toLowerCase();
  return v === '1' || v === 'true' || v === 'yes' || v === 'on';
}

function envNumber(name: string, defaultValue: number): number {
  const raw = process.env[name];
  if (raw == null || raw.trim() === '') return defaultValue;
  return Number(raw);
}

export function createApp(options: AppOptions = {}) {
  const clock: Clock = options.clock ?? Date.now;
  const nowIso = () => new Date(clock()).toISOString();

  const app = express();

  const REQUIRE_API_KEY = envBool('MCP_REQUIRE_API_KEY', true);
  const MCP_API_KEY = (process.env.MCP_API_KEY ?? '').trim();
  const RATE_LIMIT_ENABLED = envBool('MCP_RATE_LIMIT_ENABLED', true);
  const RATE_LIMIT_RPS = envNumber('MCP_RATE_LIMIT_RPS', 2);
  const RATE_LIMIT_BURST = envNumber('MCP_RATE_LIMIT_BURST', 5);
  const RATE_SALT = crypto.randomBytes(16).toString('hex');
  const rateState = new Map<string, { tokens: number; last: number }>();

// Enhanced types
interface Slot {
  time: string;
  duration_minutes: number;
}

interface SlotsResponse {
  date: string;
  slots: Slot[];
}

interface ErrorResponse {
  error: string;
  message?: string;
  timestamp: string;
}

  // Middleware
  app.use(express.json());

// Request logging middleware for observability
  app.use((req: Request, res: Response, next: NextFunction) => {
    const start = clock();
    res.on('finish', () => {
      const duration = clock() - start;
      console.log(
        JSON.stringify({
          method: req.method,
          path: req.path,
          status: res.statusCode,
          duration_ms: duration,
          timestamp: nowIso()
        })
      );
    });
    next();
  });

  const toolsAuthAndRateLimit: RequestHandler = (req, res, next) => {
    // Auth + rate-limit only for tools endpoints
    if (!req.path.startsWith('/tools/')) return next();

    if (REQUIRE_API_KEY && !MCP_API_KEY) {
      return res.status(503).json({
        error: 'Auth misconfigured',
        timestamp: nowIso()
      });
    }

    if (REQUIRE_API_KEY) {
      const provided = (req.header('X-API-Key') ?? '').trim();
      if (!provided || provided !== MCP_API_KEY) {
        return res.status(401).json({
          error: 'Unauthorized',
          timestamp: nowIso()
        });
      }
    }

    if (!RATE_LIMIT_ENABLED) return next();
    if (!Number.isFinite(RATE_LIMIT_RPS) || !Number.isFinite(RATE_LIMIT_BURST) || RATE_LIMIT_RPS <= 0 || RATE_LIMIT_BURST <= 0) {
      return res.status(503).json({
        error: 'Rate limit misconfigured',
        timestamp: nowIso()
      });
    }

    const identitySource = REQUIRE_API_KEY
      ? `key:${(req.header('X-API-Key') ?? '').trim()}`
      : `ip:${req.ip}`;
    const identity = crypto.createHash('sha256').update(`${RATE_SALT}:${identitySource}`).digest('hex').slice(0, 16);

    const nowSeconds = clock() / 1000;
    const state = rateState.get(identity) ?? { tokens: RATE_LIMIT_BURST, last: nowSeconds };
    const elapsed = Math.max(0, nowSeconds - state.last);
    const tokens = Math.min(RATE_LIMIT_BURST, state.tokens + elapsed * RATE_LIMIT_RPS);

    if (tokens < 1) {
      const retryAfter = Math.max(1, Math.ceil((1 - tokens) / RATE_LIMIT_RPS));
      res.setHeader('Retry-After', String(retryAfter));
      return res.status(429).json({
        error: 'Too Many Requests',
        timestamp: nowIso()
      });
    }

    rateState.set(identity, { tokens: tokens - 1, last: nowSeconds });
    next();
  };

  app.use(toolsAuthAndRateLimit);

// Health check endpoint
  app.get('/health', (req: Request, res: Response) => {
    res.json({
      status: 'healthy',
      service: 'MCP Tool Server',
      uptime: process.uptime(),
      timestamp: nowIso()
    });
  });

/**
 * GET /tools/get_free_slots
 * 
 * Returns available appointment slots (data-minimized - no patient names).
 * Enhanced with better validation and error handling.
 * 
 * Query parameters:
 *   - date (optional): YYYY-MM-DD format
 * 
 * Returns:
 *   { date: string, slots: Slot[] }
 */
  app.get('/tools/get_free_slots', (req: Request, res: Response, next: NextFunction) => {
    try {
      const requestedDate = req.query.date as string | undefined;
    
    // Validate date format if provided
    if (requestedDate) {
      const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
      if (!dateRegex.test(requestedDate)) {
        return res.status(400).json({
          error: 'Invalid date format. Use YYYY-MM-DD',
          timestamp: nowIso()
        });
      }
      
      // Additional validation: Check if date is valid
      const parsedDate = new Date(requestedDate);
      if (isNaN(parsedDate.getTime())) {
        return res.status(400).json({
          error: 'Invalid date value',
          timestamp: nowIso()
        });
      }
      
      // Optional: Validate date is not too far in the past or future
      const today = new Date();
      const maxFutureDate = new Date();
      maxFutureDate.setFullYear(today.getFullYear() + 1);
      
      if (parsedDate < today || parsedDate > maxFutureDate) {
        return res.status(400).json({
          error: 'Date must be between today and one year from now',
          timestamp: nowIso()
        });
      }
    }
    
    // Return sample free slots (data-minimized - no patient information)
    // In production, this would query a database for actual availability
    const freeSlots: Slot[] = [
      { time: '09:00', duration_minutes: 30 },
      { time: '09:30', duration_minutes: 30 },
      { time: '10:30', duration_minutes: 30 },
      { time: '11:00', duration_minutes: 30 },
      { time: '14:00', duration_minutes: 30 },
      { time: '14:30', duration_minutes: 30 },
      { time: '15:30', duration_minutes: 30 },
      { time: '16:00', duration_minutes: 30 }
    ];
    
    const response: SlotsResponse = {
      date: requestedDate || nowIso().split('T')[0],
      slots: freeSlots
    };
    
      res.json(response);
    } catch (error) {
      next(error);
    }
  });

// Root endpoint
  app.get('/', (req: Request, res: Response) => {
    res.json({
      service: 'MCP Tool Server',
      version: '1.0.0',
      endpoints: [
        { method: 'GET', path: '/health', description: 'Health check' },
        { method: 'GET', path: '/tools/get_free_slots', description: 'Get available appointment slots' }
      ],
      timestamp: nowIso()
    });
  });

// 404 handler
  app.use((req: Request, res: Response) => {
    res.status(404).json({
      error: 'Not found',
      path: req.path,
      timestamp: nowIso()
    });
  });

// Global error handler middleware (must be after routes)
  app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
    console.error('Unhandled error:', {
      error: err.name,
      path: req.path,
      method: req.method,
      timestamp: nowIso()
    });

    const errorResponse: ErrorResponse = {
      error: 'Internal server error',
      message: process.env.NODE_ENV === 'development' ? err.name : undefined,
      timestamp: nowIso()
    };

    res.status(500).json(errorResponse);
  });

  return app;
}

function startServer() {
  const PORT = process.env.MCP_PORT || 3000;
  const app = createApp();
  let server: any;

  const gracefulShutdown = (signal: string) => {
    console.log(`\n${signal} received. Starting graceful shutdown...`);

    if (server) {
      server.close(() => {
        console.log('HTTP server closed');
        console.log('Graceful shutdown complete');
        process.exit(0);
      });

      setTimeout(() => {
        console.error('Forceful shutdown after timeout');
        process.exit(1);
      }, 10000);
    } else {
      process.exit(0);
    }
  };

  process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
  process.on('SIGINT', () => gracefulShutdown('SIGINT'));

  server = app.listen(PORT, () => {
    console.log(JSON.stringify({
      message: `MCP Tool Server running on port ${PORT}`,
      port: PORT,
      environment: process.env.NODE_ENV || 'development',
      timestamp: new Date().toISOString()
    }));
    console.log(`Health check: http://localhost:${PORT}/health`);
    console.log(`Free slots: http://localhost:${PORT}/tools/get_free_slots`);
  });

  process.on('uncaughtException', (error: Error) => {
    console.error('Uncaught Exception:', {
      error: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString()
    });
    gracefulShutdown('uncaughtException');
  });

  process.on('unhandledRejection', (reason: any) => {
    console.error('Unhandled Rejection:', {
      reason: reason,
      timestamp: new Date().toISOString()
    });
    gracefulShutdown('unhandledRejection');
  });
}

// Start server only when executed directly (avoid side effects in tests)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
declare const require: any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
declare const module: any;

if (typeof require !== 'undefined' && typeof module !== 'undefined' && require.main === module) {
  startServer();
}

export default createApp();
