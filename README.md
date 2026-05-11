# Study Web

Study Web là web học tập full-stack bằng FastAPI, Jinja2 và SQLite. Phiên bản đầu hỗ trợ tài khoản, môn học, bài học, bài tập tương tác, dashboard tiến độ và admin CRUD nội dung.

## Chạy local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Mở `http://127.0.0.1:8036`.

Nếu cần đổi port tạm thời:

```powershell
$env:PORT=8036
python run.py
```

## Tài khoản admin

User đầu tiên đăng ký sẽ tự động là admin. Các user sau là student.

## Nội dung seed

App tự tạo database SQLite và seed môn `Lập trình Python` khi chạy lần đầu.

Mỗi môn nằm trong một folder riêng tại `app/content/subjects/`. Ví dụ môn Python nằm ở `app/content/subjects/python/subject.json`.

## Test

```powershell
pytest
```
