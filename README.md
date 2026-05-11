# Study Web

Study Web là web học tập full-stack bằng FastAPI, Jinja2 và SQLite. Phiên bản đầu hỗ trợ tài khoản, môn học, bài học, bài tập tương tác, dashboard tiến độ và admin CRUD nội dung.

## Clone repo

```powershell
git clone https://github.com/buidangminh23/Study-Web.git
cd Study-Web
```

## Chạy local trên Windows

```powershell
.\scripts\setup.ps1
.\scripts\dev.ps1
```

Mở `http://127.0.0.1:8036`.

Nếu PowerShell chặn script:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Chạy local trên macOS/Linux

```bash
chmod +x scripts/setup.sh scripts/dev.sh
./scripts/setup.sh
./scripts/dev.sh
```

Mở `http://127.0.0.1:8036`.

## Chạy thủ công

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Nếu cần đổi port tạm thời:

```powershell
$env:PORT=8036
python run.py
```

Trên macOS/Linux:

```bash
PORT=8036 python run.py
```

## Làm việc chung

- Mỗi người clone repo về máy riêng.
- Không commit `.venv`, `study_web.db`, `.env` hoặc cache local.
- Mỗi người chạy `scripts/setup` một lần, sau đó dùng `scripts/dev` để mở web.
- File nội dung môn học nằm trong `app/content/subjects/`.
- Khi sửa code xong, chạy test trước khi push.

## Tài khoản admin

User đầu tiên đăng ký trên máy của mỗi người sẽ tự động là admin. Database local `study_web.db` không đưa lên GitHub.

## Nội dung seed

App tự tạo database SQLite và seed môn `Lập trình Python` khi chạy lần đầu.

Mỗi môn nằm trong một folder riêng tại `app/content/subjects/`. Ví dụ môn Python nằm ở `app/content/subjects/python/subject.json`.

## Test

```powershell
python -m pytest
```
