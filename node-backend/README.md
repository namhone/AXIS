# AXIS Node.js Authentication Service

Service Express + Mongoose độc lập, sử dụng dual-token JWT và refresh-token rotation.

## Chạy local

```powershell
cd node-backend
npm install
Copy-Item .env.example .env
# Khởi động MongoDB và chỉnh MONGODB_URI nếu cần
npm run check
npm start
```

## API

- `POST /api/auth/register` — tạo tài khoản và cấp token.
- `POST /api/auth/login` — đăng nhập; refresh token chỉ nằm trong HttpOnly cookie.
- `POST /api/auth/refresh-token` — rotate access/refresh token.
- `POST /api/auth/logout` — xóa refresh session và cookie.
- `GET /api/auth/me` — yêu cầu `Authorization: Bearer <access-token>`.
- `GET /health` — health check.

Trong production, đặt `NODE_ENV=production`, dùng secret ngẫu nhiên riêng cho access/refresh JWT, HTTPS, và `FRONTEND_ORIGIN` chính xác. Không commit `.env`.
