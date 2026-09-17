const crypto = require('crypto');
const argon2 = require('argon2');
const mongoose = require('mongoose');

const ARGON2_OPTIONS = {
  type: argon2.argon2id,
  memoryCost: 65536,
  timeCost: 3,
  parallelism: 4,
};

const userSchema = new mongoose.Schema(
  {
    email: {
      type: String,
      required: true,
      unique: true,
      lowercase: true,
      trim: true,
      index: true,
      match: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    },
    password: {
      type: String,
      required: true,
      minlength: 8,
      select: false,
    },
    role: {
      type: String,
      enum: ['user', 'admin'],
      default: 'user',
    },
    refreshTokenHash: {
      type: String,
      default: null,
      select: false,
    },
  },
  { timestamps: true }
);

userSchema.pre('save', async function hashPassword(next) {
  if (!this.isModified('password')) {
    return next();
  }
  this.password = await argon2.hash(this.password, ARGON2_OPTIONS);
  return next();
});

userSchema.methods.comparePassword = function comparePassword(plainPassword) {
  return argon2.verify(this.password, plainPassword);
};

userSchema.methods.hashToken = function hashToken(token) {
  return crypto.createHash('sha256').update(token, 'utf8').digest('hex');
};

userSchema.methods.storeRefreshToken = async function storeRefreshToken(token) {
  this.refreshTokenHash = this.hashToken(token);
  await this.save({ validateModifiedOnly: true });
};

userSchema.methods.verifyRefreshToken = function verifyRefreshToken(token) {
  if (!this.refreshTokenHash) {
    return false;
  }
  const providedHash = Buffer.from(this.hashToken(token), 'hex');
  const storedHash = Buffer.from(this.refreshTokenHash, 'hex');
  // Kiểm tra độ dài trước để timingSafeEqual không ném lỗi.
  if (providedHash.length !== storedHash.length) {
    return false;
  }
  return crypto.timingSafeEqual(providedHash, storedHash);
};

userSchema.methods.clearRefreshToken = async function clearRefreshToken() {
  this.refreshTokenHash = null;
  await this.save({ validateModifiedOnly: true });
};

module.exports = mongoose.model('User', userSchema);
