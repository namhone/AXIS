require('dotenv').config();

const express = require('express');
const cookieParser = require('cookie-parser');
const cors = require('cors');
const helmet = require('helmet');
const mongoSanitize = require('express-mongo-sanitize');
const rateLimit = require('express-rate-limit');
const authRoutes = require('./routes/authRoutes');

const app = express();
const isProduction = process.env.NODE_ENV === 'production';
const allowedOrigins = (process.env.FRONTEND_ORIGIN || '')
  .split(',')
  .map((origin) => origin.trim())
  .filter(Boolean);
const trustedOrigins = allowedOrigins.length > 0
  ? allowedOrigins
  : ['http://localhost:5500', 'http://127.0.0.1:5500'];

const hasStrongProductionSecrets =
  typeof process.env.JWT_ACCESS_SECRET === 'string' &&
  process.env.JWT_ACCESS_SECRET.length >= 32 &&
  typeof process.env.JWT_REFRESH_SECRET === 'string' &&
  process.env.JWT_REFRESH_SECRET.length >= 32;

if (isProduction && (allowedOrigins.length === 0 || !hasStrongProductionSecrets)) {
  throw new Error(
    'Production requires FRONTEND_ORIGIN and JWT secrets of at least 32 characters'
  );
}

app.set('trust proxy', isProduction ? 1 : 0);
app.use(helmet());
app.use(cors({
  origin: (origin, callback) => {
    if (!origin || trustedOrigins.includes(origin)) {
      return callback(null, true);
    }
    return callback(new Error('CORS origin is not allowed'));
  },
  credentials: true,
}));
app.use(express.json({ limit: '16kb' }));
app.use(express.urlencoded({ extended: false, limit: '16kb' }));
app.use(cookieParser());
// Sanitize trước khi route/controller đọc dữ liệu từ request.
app.use(mongoSanitize());

const authRateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: 10,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  message: { status: 'error', code: 'RATE_LIMITED', message: 'Too many authentication requests' },
});

app.get('/health', (_req, res) => res.json({ status: 'success', message: 'ok' }));
app.use('/api/auth/register', authRateLimiter);
app.use('/api/auth/login', authRateLimiter);
app.use('/api/auth', authRoutes);

app.use((error, _req, res, _next) => {
  if (error?.type === 'entity.parse.failed') {
    return res.status(400).json({ status: 'error', code: 'INVALID_JSON', message: 'Request body is invalid JSON' });
  }
  console.error(error);
  return res.status(500).json({ status: 'error', code: 'INTERNAL_ERROR', message: 'An unexpected error occurred' });
});

module.exports = app;
