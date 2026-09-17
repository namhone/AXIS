const mongoose = require('mongoose');
const User = require('../models/User');
const {
  createAccessToken,
  createRefreshToken,
  verifyRefreshToken,
} = require('../security/jwt');

const COOKIE_NAME = process.env.COOKIE_NAME || 'axis_refresh_token';

function cookieOptions() {
  const isProduction = process.env.NODE_ENV === 'production';
  return {
    httpOnly: true,
    // Cross-domain frontend/backend trên HTTPS cần SameSite=None và Secure.
    sameSite: isProduction ? 'none' : 'strict',
    secure: isProduction,
    path: '/api/auth',
    maxAge: 7 * 24 * 60 * 60 * 1000,
  };
}

function clearRefreshCookie(res) {
  res.clearCookie(COOKIE_NAME, cookieOptions());
}

function setRefreshCookie(res, token) {
  res.cookie(COOKIE_NAME, token, cookieOptions());
}

function normalizeEmail(value) {
  return typeof value === 'string' ? value.trim().toLowerCase() : '';
}

function validEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function publicUser(user) {
  return { id: user._id.toString(), email: user.email, role: user.role };
}

async function issueTokenPair(user, res, expectedRefreshTokenHash = null) {
  const accessToken = createAccessToken(user);
  const refreshToken = createRefreshToken(user);
  const nextRefreshTokenHash = user.hashToken(refreshToken);

  if (expectedRefreshTokenHash) {
    // Compare-and-swap giúp chỉ một request đồng thời được phép rotate token.
    const rotation = await User.updateOne(
      { _id: user._id, refreshTokenHash: expectedRefreshTokenHash },
      { $set: { refreshTokenHash: nextRefreshTokenHash } }
    );
    if (rotation.matchedCount !== 1) {
      const reuseError = new Error('Refresh token reuse detected');
      reuseError.code = 'TOKEN_REUSE_DETECTED';
      throw reuseError;
    }
  } else {
    user.refreshTokenHash = nextRefreshTokenHash;
    await user.save({ validateModifiedOnly: true });
  }

  setRefreshCookie(res, refreshToken);
  return { accessToken, user: publicUser(user) };
}

async function register(req, res, next) {
  try {
    const email = normalizeEmail(req.body.email);
    const password = req.body.password;
    if (!validEmail(email)) {
      return res.status(400).json({ status: 'error', code: 'INVALID_EMAIL', message: 'Email is invalid' });
    }
    if (typeof password !== 'string' || password.length < 8) {
      return res.status(400).json({
        status: 'error',
        code: 'WEAK_PASSWORD',
        message: 'Password must be at least 8 characters',
      });
    }
    const existingUser = await User.exists({ email });
    if (existingUser) {
      return res.status(409).json({ status: 'error', code: 'EMAIL_EXISTS', message: 'Email is already registered' });
    }
    const user = await User.create({ email, password });
    return res.status(201).json({ status: 'success', data: await issueTokenPair(user, res) });
  } catch (error) {
    if (error?.code === 11000) {
      return res.status(409).json({ status: 'error', code: 'EMAIL_EXISTS', message: 'Email is already registered' });
    }
    return next(error);
  }
}

async function login(req, res, next) {
  try {
    const email = normalizeEmail(req.body.email);
    const password = req.body.password;
    const user = await User.findOne({ email }).select('+password +refreshTokenHash');
    if (!user || typeof password !== 'string' || !(await user.comparePassword(password))) {
      return res.status(401).json({ status: 'error', code: 'INVALID_CREDENTIALS', message: 'Email or password is incorrect' });
    }
    return res.json({ status: 'success', data: await issueTokenPair(user, res) });
  } catch (error) {
    return next(error);
  }
}

async function refreshToken(req, res, next) {
  const token = req.cookies?.[COOKIE_NAME];
  let refreshUserId = null;
  if (!token) {
    return res.status(401).json({ status: 'error', code: 'REFRESH_TOKEN_REQUIRED', message: 'Refresh token is required' });
  }

  try {
    const payload = verifyRefreshToken(token);
    if (payload.type !== 'refresh' || !mongoose.isValidObjectId(payload.sub)) {
      clearRefreshCookie(res);
      return res.status(401).json({ status: 'error', code: 'INVALID_REFRESH_TOKEN', message: 'Refresh token is invalid' });
    }
    refreshUserId = payload.sub;
    const user = await User.findById(payload.sub).select('+refreshTokenHash');
    if (!user) {
      clearRefreshCookie(res);
      return res.status(401).json({ status: 'error', code: 'INVALID_REFRESH_TOKEN', message: 'Refresh token is invalid' });
    }
    if (!user.verifyRefreshToken(token)) {
      await user.clearRefreshToken();
      clearRefreshCookie(res);
      return res.status(403).json({ status: 'error', code: 'TOKEN_REUSE_DETECTED', message: 'Refresh token reuse detected; all sessions were revoked' });
    }
    const previousRefreshTokenHash = user.refreshTokenHash;
    const data = await issueTokenPair(user, res, previousRefreshTokenHash);
    return res.json({ status: 'success', data });
  } catch (error) {
    if (error?.code === 'TOKEN_REUSE_DETECTED') {
      if (refreshUserId) {
        await User.findByIdAndUpdate(refreshUserId, { $set: { refreshTokenHash: null } });
      }
      clearRefreshCookie(res);
      return res.status(403).json({
        status: 'error',
        code: 'TOKEN_REUSE_DETECTED',
        message: 'Refresh token reuse detected; all sessions were revoked',
      });
    }
    clearRefreshCookie(res);
    if (error.name === 'TokenExpiredError') {
      return res.status(401).json({ status: 'error', code: 'REFRESH_TOKEN_EXPIRED', message: 'Refresh token has expired' });
    }
    if (error.name === 'JsonWebTokenError') {
      return res.status(401).json({ status: 'error', code: 'INVALID_REFRESH_TOKEN', message: 'Refresh token is invalid' });
    }
    return next(error);
  }
}

async function logout(req, res, next) {
  try {
    const token = req.cookies?.[COOKIE_NAME];
    if (token) {
      try {
        const payload = verifyRefreshToken(token);
        if (mongoose.isValidObjectId(payload.sub)) {
          await User.findByIdAndUpdate(payload.sub, { $set: { refreshTokenHash: null } });
        }
      } catch (error) {
        if (error.name !== 'TokenExpiredError' && error.name !== 'JsonWebTokenError') {
          throw error;
        }
      }
    }
    clearRefreshCookie(res);
    return res.json({ status: 'success', code: 'LOGGED_OUT', message: 'Session ended' });
  } catch (error) {
    return next(error);
  }
}

async function me(req, res, next) {
  try {
    const user = await User.findById(req.user.sub);
    if (!user) {
      return res.status(404).json({ status: 'error', code: 'USER_NOT_FOUND', message: 'User was not found' });
    }
    return res.json({ status: 'success', data: { user: publicUser(user) } });
  } catch (error) {
    return next(error);
  }
}

module.exports = { register, login, refreshToken, logout, me };
