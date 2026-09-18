# MongoDB Atlas và Render

## MongoDB Atlas

Tạo database user riêng cho service, giới hạn Network Access theo IP của
provider deploy, rồi đặt biến:

```env
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/axis_auth?retryWrites=true&w=majority
```

Không commit chuỗi kết nối thật vào Git.

## Render

File `../render.yaml` tạo hai web service:

- `axis-api`: FastAPI profile/dashboard/account API.
- `axis-auth-service`: Node.js authentication service.

Service FastAPI dùng:

- `pip install -r requirements.txt` làm build command.
- `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` làm start command.
- `/health` làm health check.
- `DATABASE_URL`, `CORS_ORIGINS` và `GROQ_API_KEY` cần nhập trong Render Dashboard.

Service Node dùng:

- `npm ci` làm build command.
- `npm start` làm start command.
- `/health` làm health check.
- JWT secrets được Render tự sinh.
- `MONGODB_URI` và `FRONTEND_ORIGIN` cần nhập trong Render Dashboard.

`FRONTEND_ORIGIN` phải là URL HTTPS chính xác của frontend. Cookie production
dùng `HttpOnly`, `Secure` và `SameSite=None` để frontend và backend khác domain
trao đổi refresh cookie.

Sau khi Render tạo hai service, dùng URL của `axis-api` làm API base cho
frontend (`https://axis-api.onrender.com/api/v1`) và dùng URL frontend làm
`CORS_ORIGINS` của FastAPI cũng như `FRONTEND_ORIGIN` của Node.

Mongoose dùng connection pool giới hạn 2-10 kết nối, timeout chọn server 10 giây,
timeout kết nối 10 giây và socket timeout 45 giây để tránh request treo vô hạn
khi Atlas không khả dụng.

## Frontend API URL

Frontend hiện vẫn dùng FastAPI `/api/v1` cho profile, dashboard và account.
Có thể override URL FastAPI bằng cách đặt trước `js/auth.js`:

```html
<script>
  window.FUTUREPATH_API_BASE = 'https://api.example.com/api/v1/auth';
</script>
<script src="/js/auth.js"></script>
```

Node auth service dùng API riêng `/api/auth`. Không đổi `FUTUREPATH_API_BASE`
sang Node service cho đến khi các route profile/dashboard được triển khai tương
ứng trên Node.
