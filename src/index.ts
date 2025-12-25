/**
 * Minimal MCP Tool Server for SecureDoc Flow
 * 
 * Provides data-minimizing tool endpoints, starting with free appointment slots.
 */

import express, { Request, Response } from 'express';

const app = express();
const PORT = process.env.MCP_PORT || 3000;

// Middleware
app.use(express.json());

// Health check endpoint
app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'healthy', service: 'MCP Tool Server' });
});

/**
 * GET /tools/get_free_slots
 * 
 * Returns available appointment slots (data-minimized - no patient names).
 * This is intentionally minimal and privacy-focused.
 * 
 * Query parameters:
 *   - date (optional): YYYY-MM-DD format
 * 
 * Returns:
 *   { slots: [{ time: "HH:MM", duration_minutes: number }, ...] }
 */
app.get('/tools/get_free_slots', (req: Request, res: Response) => {
  const requestedDate = req.query.date as string;
  
  // Validate date format if provided
  if (requestedDate) {
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(requestedDate)) {
      return res.status(400).json({
        error: 'Invalid date format. Use YYYY-MM-DD'
      });
    }
  }
  
  // Return sample free slots (data-minimized - no patient information)
  // In production, this would query a database for actual availability
  const freeSlots = [
    { time: '09:00', duration_minutes: 30 },
    { time: '09:30', duration_minutes: 30 },
    { time: '10:30', duration_minutes: 30 },
    { time: '11:00', duration_minutes: 30 },
    { time: '14:00', duration_minutes: 30 },
    { time: '14:30', duration_minutes: 30 },
    { time: '15:30', duration_minutes: 30 },
    { time: '16:00', duration_minutes: 30 }
  ];
  
  res.json({
    date: requestedDate || new Date().toISOString().split('T')[0],
    slots: freeSlots
  });
});

// Root endpoint
app.get('/', (req: Request, res: Response) => {
  res.json({
    service: 'MCP Tool Server',
    version: '1.0.0',
    endpoints: [
      { method: 'GET', path: '/health', description: 'Health check' },
      { method: 'GET', path: '/tools/get_free_slots', description: 'Get available appointment slots' }
    ]
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`MCP Tool Server running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`Free slots: http://localhost:${PORT}/tools/get_free_slots`);
});

export default app;
