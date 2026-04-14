# Service Development Rules

## Vai trò

Đây là phần **Service** dùng để xử lý **logic nghiệp vụ (Business Logic)** trong hệ thống.

Bạn là một **Senior Backend Developer sử dụng FastAPI**, vì vậy Service phải được thiết kế theo chuẩn **Clean Architecture**, tối ưu hiệu năng và dễ mở rộng.

Service sẽ là nơi:

* xử lý logic nghiệp vụ
* gọi Repository để thao tác dữ liệu
* tối ưu query
* xử lý dữ liệu trước khi trả về
* convert dữ liệu sang Pydantic Schema

Service **không thao tác trực tiếp với Database**.

---

## Nguyên tắc bắt buộc

* Service là nơi xử lý Business Logic
* Service sẽ gọi Repository để lấy dữ liệu
* Service không query MongoDB trực tiếp
* Service không viết query
* Service không chứa code database
* Service chỉ gọi Repository

---

## Khởi tạo Service

Service phải nhận Repository thông qua constructor.

```python
def __init__(self, category_repository: CategoryRepository):
    self._category_repository = category_repository
```

Nguyên tắc:

* luôn inject Repository vào Service
* không tự tạo Repository trong Service
* không import collection vào Service
* không thao tác MongoDB trong Service

---

## Quy tắc xử lý logic

Service phải:

* xử lý logic rõ ràng
* kiểm tra dữ liệu
* kiểm tra tồn tại
* kiểm tra điều kiện
* xử lý business rule
* tối ưu query
* trả dữ liệu chuẩn

---

## Cấm N+1 Query

Tuyệt đối cấm:

* vòng lặp gọi repository
* loop và gọi database trong loop

Ví dụ sai:

```python
for category in categories:
    await repo.get_product_by_category(category["_id"])
```

Điều này gây:

**N+1 Query**

---

## Phải tối ưu Query

Luôn tìm cách xử lý:

* O(1)
* O(N)
* O(log N)

Không được viết:

* O(N²)

---

## Cách tối ưu

Phải:

* query 1 lần
* lấy toàn bộ dữ liệu cần thiết
* xử lý bằng dict hoặc map
* xử lý trong memory
* tránh gọi repo nhiều lần
* gom query thành 1 lần gọi

Ví dụ đúng:

* repo lấy toàn bộ category
* repo lấy toàn bộ product
* service xử lý mapping

---

## Quy tắc code

Phải sử dụng:

* Python 3.12+
* FastAPI chuẩn
* Async/Await
* Clean Code

Không dùng syntax cũ.

---

## Cấm

* typing.List
* typing.Optional
* code Python cũ
* syntax Python < 3.12
* viết code lỗi thời

---

## Phải dùng

* list
* dict
* str | None
* int | None
* bool | None
* match case
* modern python syntax
* async await chuẩn

---

## Trả dữ liệu

Dữ liệu trả ra từ Service phải được convert sang **Pydantic Object**.

Ví dụ:

```python
return CategoryCreateResponse.model_validate(category_raw)
```

---

## Nguyên tắc trả dữ liệu

Service phải trả:

* Pydantic Schema
* không trả dict thô
* không trả ObjectId
* không trả raw data

Repository trả raw data
Service convert thành schema

---

## Flow chuẩn

Controller gọi Service

Service gọi Repository

Repository trả Raw Data

Service xử lý logic

Service convert sang Schema

Service trả về Controller

Controller trả Response

---

## Kiến trúc chuẩn

Repository:

Database → Raw Data

Service:

Raw Data → Business Logic → Pydantic Schema

Controller:

Schema → JSON Response

---

## Tóm tắt

Service có nhiệm vụ:

* xử lý business logic
* gọi repository
* tối ưu query
* tránh N+1
* không loop gọi repo
* dùng Python 3.12+
* convert sang Pydantic
* trả schema
* clean code
* chuẩn fastapi backend
