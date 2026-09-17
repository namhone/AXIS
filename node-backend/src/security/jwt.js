const crypto = require('crypto');
const jwt = require('jsonwebtoken');

function getSecret(name) {
  const secret = process.env[name];
  if (!secret || secret.length < 32) {
    throw new Error(`${name} must be at least 32 characters long`);
  }
  return secret;
}

function createAccessToken(user) {
  return jwt.sign(
    { sub: user._id.toString(), email: user.email, role: user.role, type: 'access' },
    getSecret('JWT_ACCESS_SECRET'),
    { expiresIn: process.env.JWT_ACCESS_EXPIRES_IN || '15m' }
  );
}

function createRefreshToken(user) {
  return jwt.sign(
    {
      sub: user._id.toString(),
      type: 'refresh',
      // jti bảo đảm mỗi lần rotation tạo chuỗi JWT mới kể cả trong cùng một giây.
      jti: crypto.randomUUID(),
    },
    getSecret('JWT_REFRESH_SECRET'),
    { expiresIn: process.env.JWT_REFRESH_EXPIRES_IN || '7d' }
  );
}

function verifyAccessToken(token) {
  return jwt.verify(token, getSecret('JWT_ACCESS_SECRET'), { algorithms: ['HS256'] });
}

function verifyRefreshToken(token) {
  return jwt.verify(token, getSecret('JWT_REFRESH_SECRET'), { algorithms: ['HS256'] });
}

module.exports = {
  createAccessToken,
  createRefreshToken,
  verifyAccessToken,
  verifyRefreshToken,
};
