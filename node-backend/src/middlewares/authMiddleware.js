const { TokenExpiredError, JsonWebTokenError } = require('jsonwebtoken');
const { verifyAccessToken } = require('../security/jwt');

function sendAuthError(res, status, code, message) {
  return res.status(status).json({ status: 'error', code, message });
}

function authenticate(req, res, next) {
  const authorization = req.get('Authorization');
  if (!authorization || !authorization.startsWith('Bearer ')) {
    return sendAuthError(
      res,
      401,
      'ACCESS_TOKEN_REQUIRED',
      'Authorization Bearer token is required'
    );
  }

  const token = authorization.slice('Bearer '.length).trim();
  if (!token) {
    return sendAuthError(res, 401, 'ACCESS_TOKEN_REQUIRED', 'Access token is required');
  }

  try {
    const payload = verifyAccessToken(token);
    if (payload.type !== 'access' || typeof payload.sub !== 'string') {
      return sendAuthError(res, 401, 'INVALID_TOKEN', 'Access token is invalid');
    }
    req.user = payload;
    return next();
  } catch (error) {
    if (error instanceof TokenExpiredError) {
      return sendAuthError(res, 401, 'ACCESS_TOKEN_EXPIRED', 'Access token has expired');
    }
    if (error instanceof JsonWebTokenError || error instanceof Error) {
      return sendAuthError(res, 401, 'INVALID_TOKEN', 'Access token is invalid');
    }
    return next(error);
  }
}

module.exports = { authenticate };
