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

const app = express();
const PORT = process.env.MCP_PORT || 3000;

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
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(
      JSON.stringify({
        method: req.method,
        path: req.path,
        status: res.statusCode,
        duration_ms: duration,
        timestamp: new Date().toISOString()
      })
    );
  });
  next();
});

// Global error handler middleware
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  console.error('Unhandled error:', {
    error: err.message,
    stack: err.stack,
    path: req.path,
    method: req.method,
    timestamp: new Date().toISOString()
  });
  
  const errorResponse: ErrorResponse = {
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined,
    timestamp: new Date().toISOString()
  };
  
  res.status(500).json(errorResponse);
});

// Health check endpoint
app.get('/health', (req: Request, res: Response) => {
  res.json({ 
    status: 'healthy', 
    service: 'MCP Tool Server',
    uptime: process.uptime(),
    timestamp: new Date().toISOString()
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
          timestamp: new Date().toISOString()
        });
      }
      
      // Additional validation: Check if date is valid
      const parsedDate = new Date(requestedDate);
      if (isNaN(parsedDate.getTime())) {
        return res.status(400).json({
          error: 'Invalid date value',
          timestamp: new Date().toISOString()
        });
      }
      
      // Optional: Validate date is not too far in the past or future
      const today = new Date();
      const maxFutureDate = new Date();
      maxFutureDate.setFullYear(today.getFullYear() + 1);
      
      if (parsedDate < today || parsedDate > maxFutureDate) {
        return res.status(400).json({
          error: 'Date must be between today and one year from now',
          timestamp: new Date().toISOString()
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
      date: requestedDate || new Date().toISOString().split('T')[0],
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
    timestamp: new Date().toISOString()
  });
});

// 404 handler
app.use((req: Request, res: Response) => {
  res.status(404).json({
    error: 'Not found',
    path: req.path,
    timestamp: new Date().toISOString()
  });
});

// Server instance for graceful shutdown
let server: any;

// Graceful shutdown handler
const gracefulShutdown = (signal: string) => {
  console.log(`\n${signal} received. Starting graceful shutdown...`);
  
  if (server) {
    server.close(() => {
      console.log('HTTP server closed');
      console.log('Graceful shutdown complete');
      process.exit(0);
    });
    
    // Force shutdown after 10 seconds
    setTimeout(() => {
      console.error('Forceful shutdown after timeout');
      process.exit(1);
    }, 10000);
  } else {
    process.exit(0);
  }
};

// Register shutdown handlers
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Start server
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

// Handle uncaught exceptions
process.on('uncaughtException', (error: Error) => {
  console.error('Uncaught Exception:', {
    error: error.message,
    stack: error.stack,
    timestamp: new Date().toISOString()
  });
  gracefulShutdown('uncaughtException');
});

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason: any) => {
  console.error('Unhandled Rejection:', {
    reason: reason,
    timestamp: new Date().toISOString()
  });
  gracefulShutdown('unhandledRejection');
});

export default app;
