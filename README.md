# FuturePath

FuturePath là giao diện web hỗ trợ học sinh khám phá nghề nghiệp, tự đánh giá năng lực và lập lộ trình phát triển cá nhân. Phiên bản hiện tại là **frontend prototype**, phù hợp để trình bày UX, kiểm thử luồng người dùng và chuẩn bị tích hợp backend/AI.

## Chức năng hiện có

- Trang chủ giới thiệu FuturePath, tiến độ hồ sơ và các công cụ chính.
- Hồ sơ cá nhân:
  - Họ tên, năm sinh, lớp, email, số điện thoại, LinkedIn.
  - Mục tiêu và phần giới thiệu bản thân.
  - Lưu tự động trên trình duyệt.
  - Tính phần trăm hoàn thiện hồ sơ dùng chung giữa các trang.
  - Giao diện tải lên/xuất PDF hồ sơ.
- Đánh giá năng lực:
  - Bộ câu hỏi đánh giá kỹ năng.
  - Hiển thị điểm kỹ năng và nghề nghiệp đề xuất.
  - Lưu kết quả đánh giá và danh sách đề xuất trên trình duyệt.
- Lộ trình phát triển:
  - Tạo mục tiêu theo ngày bằng lịch.
  - Thiết lập số phút học mỗi ngày và ghi chú.
  - Tính tiến độ dựa trên nhiệm vụ đã đến hạn.
  - Cảnh báo nhiệm vụ quá hạn chưa hoàn thành.
  - Lộ trình mẫu gồm các bước học.
  - Hai trạng thái: `Chưa học` và `Đã học`.
  - Nút `Bắt đầu` mở Pomodoro theo thời lượng kế hoạch.
  - Đánh dấu hoàn thành để cập nhật tiến độ.
- Thư viện nghề nghiệp:
  - Danh sách nghề mẫu.
  - Trang chi tiết nghề theo tham số URL, ví dụ `career-detail.html?career=developer`.
- Xác thực demo:
  - Modal đăng nhập/đăng ký.
  - Nút Google OAuth hiện chỉ là giao diện placeholder, chưa xác thực thật.
- Giao diện:
  - Phong cách minimalist/editorial, màu trung tính và pastel nhẹ.
  - Header dùng chung, sticky khi cuộn.
  - Menu ngang khi đủ không gian.
  - Menu mobile khi màn hình nhỏ, có cả đăng nhập/đăng ký.
  - Responsive cho desktop, tablet và mobile.
  - Hiệu ứng hover, focus, chuyển cảnh và lắc nhẹ nhiệm vụ chưa học.
  - Hỗ trợ `prefers-reduced-motion`.

## Cấu trúc dự án

```text
FuturePath/
├── index.html                 # Trang chủ
├── css/
│   └── global.css             # Theme, layout, responsive và animation
├── js/
│   └── app.js                 # Dữ liệu dùng chung và đồng bộ hồ sơ
├── pages/
│   ├── profile.html           # Hồ sơ cá nhân
│   ├── assessment.html        # Đánh giá năng lực
│   ├── development.html       # Mục tiêu và lộ trình phát triển
│   ├── careers.html           # Thư viện nghề nghiệp
│   ├── career-detail.html     # Chi tiết một nghề
│   └── about.html             # Giới thiệu dự án
├── assets/                    # Ảnh minh họa và biểu đồ
├── data/
│   └── submissions.json       # Dữ liệu form runtime (không commit)
├── server.py                  # Flask server demo cho form liên hệ
└── scripts/
    └── import_submissions.ps1 # Script hỗ trợ import dữ liệu
```

Các file `.bak` là bản sao lưu trong quá trình thiết kế. Có thể giữ lại để tham khảo hoặc loại khỏi repository trước khi phát hành chính thức.
File `.gitignore` đã loại cache Python, file môi trường và dữ liệu form runtime khỏi lần commit đầu tiên.

## Chạy dự án trên máy

### Cách 1: Chạy bằng Python server tích hợp

Yêu cầu Python 3:

```powershell
cd D:\FileCuaNam\KhoaHocKiThuat\FuturePath
python server.py
```

Mở trình duyệt tại:

```text
http://127.0.0.1:5000/
```

`server.py` hiện có hai endpoint demo:

- `POST /submit`: nhận `email`, `phone`, `message` và ghi vào `data/submissions.json`.
- `GET /list`: đọc danh sách form đã gửi.

### Cách 2: Chạy static server

Nếu chỉ cần xem frontend và không cần endpoint form liên hệ:

```powershell
cd D:\FileCuaNam\KhoaHocKiThuat\FuturePath
python -m http.server 8000
```

Mở `http://127.0.0.1:8000/`.

Không nên mở trực tiếp bằng `file://` khi kiểm thử các luồng cần server, vì trình duyệt có thể giới hạn request và module tài nguyên.

## Dữ liệu frontend

Prototype hiện dùng `localStorage`, không có cơ sở dữ liệu và không đồng bộ giữa các thiết bị.

| Key | Nội dung |
|---|---|
| `futurepath.profile` | Thông tin hồ sơ cá nhân |
| `futurepath.profile_completion` | Phần trăm hoàn thiện hồ sơ dùng chung |
| `futurepath.goals` | Mục tiêu, ngày học, số phút và trạng thái hoàn thành |
| `futurepath.roadmap` | Trạng thái các bước lộ trình |
| `futurepath.last_assessment` | Kết quả đánh giá gần nhất |
| `futurepath.saved_recommendations` | Nghề nghiệp được đề xuất |
| `futurepath.signed_in` | Trạng thái đăng nhập demo trên thiết bị |

API dữ liệu dùng chung nằm trong `js/app.js` qua `window.FuturePathData`. Khi chuyển backend, đây là điểm nên thay bằng service gọi API thay vì sửa logic từng trang.

## Đưa lên GitHub

1. Tạo repository mới trên GitHub.
2. Đặt toàn bộ thư mục `FuturePath` làm thư mục gốc repository.
3. Kiểm tra không đưa dữ liệu cá nhân, API key hoặc thông tin đăng nhập vào repository.
4. Commit và push:

```powershell
cd D:\FileCuaNam\KhoaHocKiThuat\FuturePath
git init
git add .
git commit -m "Initial FuturePath frontend"
git branch -M main
git remote add origin https://github.com/<username>/<repository>.git
git push -u origin main
```

### GitHub Pages

Frontend có thể chạy trên GitHub Pages vì các trang là HTML/CSS/JavaScript tĩnh:

1. Vào `Settings` → `Pages`.
2. Chọn `Deploy from a branch`.
3. Chọn branch `main` và thư mục `/ (root)`.
4. Lưu và chờ GitHub tạo URL.

`server.py` không chạy trên GitHub Pages. Nếu cần lưu form, đăng nhập, hồ sơ hoặc kết quả đánh giá thì phải triển khai Flask/API ở một dịch vụ backend riêng.

## Lưu ý trước khi làm backend

- Đăng nhập và đăng ký hiện chỉ là UI demo; chưa có mật khẩu, session hoặc OAuth thật.
- Nút Google cần được nối với OAuth ở backend, không đặt secret ở frontend.
- Hồ sơ, mục tiêu, roadmap và đánh giá cần chuyển từ `localStorage` sang API có xác thực người dùng.
- Pomodoro hiện là timer frontend; chưa ghi nhận thời gian học thực tế và chưa tạo phiên học trong database.
- Hoàn thành roadmap hiện cộng tiến độ giao diện; backend nên lưu lịch sử hoàn thành và phiên Pomodoro để tính chính xác.
- Dữ liệu nghề nghiệp hiện là dữ liệu mẫu hard-coded. Bản production nên có nguồn tham khảo, ngày cập nhật và metadata nghề.
- Đánh giá nghề nghiệp hiện là logic prototype; AI thật nên được gọi qua backend/AI gateway.
- `server.py` là server thử nghiệm, chưa có xác thực, giới hạn request, database hoặc cấu hình production.
- CORS trong server demo đang cho phép mọi origin; cần giới hạn domain khi triển khai thật.
- Cần bổ sung kiểm tra MIME, kích thước và lưu trữ an toàn nếu hỗ trợ upload PDF production.

## Hướng phát triển đề xuất

1. Thiết kế database cho `users`, `profiles`, `goals`, `roadmap_steps`, `pomodoro_sessions` và `assessments`.
2. Xây dựng API xác thực và thay toàn bộ thao tác localStorage bằng API service.
3. Tích hợp Google OAuth ở backend.
4. Xử lý PDF ở server, chuẩn hóa dữ liệu hồ sơ và kiểm tra file an toàn.
5. Tích hợp AI gateway cho đánh giá năng lực và đề xuất nghề.
6. Bổ sung nguồn dữ liệu nghề nghiệp có trích dẫn, mức lương, kỹ năng và yêu cầu cập nhật.
7. Thêm test cho tính tiến độ, nhiệm vụ quá hạn, đồng bộ hồ sơ và trạng thái roadmap.

## Ghi chú thiết kế

Giao diện tuân theo hướng minimalist/editorial: nền sáng, đường viền mảnh, màu nhấn pastel tiết chế, khoảng trắng rộng, typography có tương phản và không dùng hình nền SVG phức tạp cho các sơ đồ dễ lỗi. Các ảnh trong `assets/` được dùng thay cho những minh họa SVG không ổn định.

## Xác nhận hoàn tất frontend

Trạng thái: **Frontend prototype đã sẵn sàng để chuyển sang thiết kế backend.**

Kiểm tra lần cuối ngày **03/09/2026**:

- [x] 7 trang chính đều tải được qua static server.
- [x] Không phát hiện lỗi JavaScript runtime khi mở các trang.
- [x] `js/app.js` và `server.py` vượt qua kiểm tra cú pháp.
- [x] Các đường dẫn tương đối tới trang và tài nguyên chính được kiểm tra.
- [x] Header, footer và navigation dùng chung trên toàn bộ trang.
- [x] Desktop có menu ngang; mobile có menu đầu trang và nút đăng nhập/đăng ký.
- [x] Header sticky, logo không lệch và không tạo tràn ngang ngoài ý muốn.
- [x] Phần trăm hoàn thiện hồ sơ lấy từ một nguồn dữ liệu dùng chung.
- [x] Hồ sơ, đánh giá, mục tiêu và roadmap có luồng lưu/đọc dữ liệu demo.
- [x] Lộ trình có hai trạng thái `Chưa học` và `Đã học`; trạng thái hoàn tất bị khóa.
- [x] Trên mobile, tag trạng thái và các nút `Bắt đầu`/`Đã học` được căn giữa card.
- [x] Pomodoro lấy số phút từ kế hoạch, có giá trị mặc định 25 phút.
- [x] Nhiệm vụ theo ngày hỗ trợ ngày thực hiện, số phút, ghi chú, hoàn thành và quá hạn.
- [x] Các card công cụ và nút CTA chính có liên kết hoặc hành vi tương ứng.
- [x] Modal đăng nhập/đăng ký đóng được bằng nút và backdrop; Google vẫn là placeholder.
- [x] Hỗ trợ chuyển động giảm nhẹ khi người dùng bật `prefers-reduced-motion`.

### Luồng demo nên kiểm tra khi trình bày

1. Từ trang chủ mở `Hồ sơ`, nhập một vài trường và quay lại để thấy phần trăm được đồng bộ.
2. Mở `Đánh giá & Gợi ý`, hoàn thành bài đánh giá và xem điểm cùng nghề đề xuất.
3. Mở `Phát triển bản thân`, thêm mục tiêu có ngày và số phút, sau đó lưu kế hoạch.
4. Bấm `Bắt đầu` ở một bước roadmap để mở Pomodoro; bấm `Đã học` để đổi trạng thái.
5. Mở `Thư viện nghề nghiệp`, chọn `Xem chi tiết` và kiểm tra tham số `career` trên URL.
6. Thu nhỏ trình duyệt để kiểm tra menu mobile, auth actions và căn giữa roadmap.
7. Thử form liên hệ khi chạy `server.py` và xác nhận dữ liệu được ghi vào `data/submissions.json`.

### Kết quả kiểm tra kỹ thuật

Static server đã được dùng để kiểm tra các route:

```text
/
/index.html
/pages/profile.html
/pages/assessment.html
/pages/development.html
/pages/careers.html
/pages/career-detail.html?career=developer
/pages/about.html
```

Các lệnh kiểm tra tối thiểu:

```powershell
node --check js/app.js
python -m py_compile server.py
python -m http.server 8000
```

Không có `package.json`, framework frontend hoặc bộ test tự động trong prototype hiện tại. Việc này là chủ ý để giữ bản demo nhẹ; backend nên bổ sung test API và test nghiệp vụ khi bắt đầu triển khai.

## Bàn giao cho backend

Frontend đang coi `window.FuturePathData` trong `js/app.js` là lớp dữ liệu dùng chung. Backend có thể giữ nguyên các selector và luồng UI, sau đó thay phần lưu cục bộ bằng API service.

### Hợp đồng dữ liệu nên giữ

- `profile`: thông tin cá nhân và mục tiêu nghề nghiệp.
- `profile_completion`: giá trị 0–100 được tính từ hồ sơ, không lấy từ điểm kỹ năng.
- `assessment`: câu trả lời, điểm kỹ năng, phiên bản bộ câu hỏi và thời gian thực hiện.
- `recommendations`: danh sách nghề, điểm phù hợp, lý do và nguồn tham khảo.
- `goals`: tiêu đề, ngày, số phút dự kiến, ghi chú, danh mục và trạng thái hoàn thành.
- `roadmap`: mã bước, trạng thái `pending`/`done`, thời điểm hoàn thành.
- `pomodoro_sessions`: bước liên quan, số phút kế hoạch, số phút thực tế, bắt đầu/kết thúc và trạng thái.

### Nguyên tắc tích hợp

- Xác thực người dùng ở backend; không lưu mật khẩu hoặc token bí mật trong frontend.
- Google OAuth chỉ xử lý qua backend/callback an toàn.
- Mỗi bản ghi dữ liệu phải gắn với user và có quyền truy cập rõ ràng.
- API cần validation, rate limiting, logging và xử lý lỗi hiển thị được cho người dùng.
- Giới hạn CORS theo domain triển khai, không dùng `*` ở production.
- Upload PDF cần kiểm tra MIME, kích thước, tên file và lưu trữ ngoài thư mục public.
- AI nên chạy qua AI gateway/backend để bảo vệ API key, kiểm soát chi phí và lưu phiên bản prompt/model.
- Khi API đã ổn định, giữ fallback localStorage chỉ cho offline/demo hoặc loại bỏ có chủ ý.
