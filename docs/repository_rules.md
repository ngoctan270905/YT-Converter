# Repository Development Rules

## Vai trò

Đây là phần Repository dùng để thao tác trực tiếp với Database (MongoDB).

Repository chỉ có nhiệm vụ:

* truy vấn dữ liệu
* thêm dữ liệu
* cập nhật dữ liệu
* xóa dữ liệu
* trả dữ liệu thô về cho Service xử lý

Repository không xử lý business logic.

---

## Nguyên tắc bắt buộc

* Repository chỉ thao tác với Database
* Không xử lý logic nghiệp vụ
* Không validate dữ liệu
* Không dùng Schema trong Repository
* Không xử lý dữ liệu phức tạp
* Chỉ trả dữ liệu thô về Service

---

## Sử dụng MongoDB Async

Bắt buộc sử dụng:

* AsyncCollection của PyMongo async
* Cấm sử dụng thư viện Mortor 

---

## Khai báo collection

```python
def __init__(self, collection: AsyncCollection):
    """
    Args:
        collection (AsyncCollection): MongoDB collection
    """
    self.collection = collection
```

---

## Quy tắc tham số hàm

### Dữ liệu thêm và sửa

Phải là:

* dict

Ví dụ:

```python
create_user(data: dict)
update_user(data: dict)
```

Không được dùng:

* Schema
* Model
* DTO

Repository chỉ nhận dict thuần.

---

### Tham số đơn

Có thể sử dụng:

* str
* int
* bool

Ví dụ:

```python
user_id: str
product_id: str
limit: int
page: int
```

---

## Cấm sử dụng Schema trong Repository

Sai:

```python
def create_user(self, user: UserCreate):
```

Đúng:

```python
def create_user(self, data: dict):
```

---

## Quy tắc trả dữ liệu

Trước khi trả dữ liệu về Service phải convert:

ObjectId → str

Ví dụ:

```python
user["_id"] = str(user["_id"])
```

---

## Nguyên tắc trả dữ liệu

Repository phải trả:

* dữ liệu thô
* dict
* list[dict]
* không dùng schema

Service sẽ là nơi xử lý tiếp.

---

## Cấm sử dụng Aggregate

Tuyệt đối cấm:

* aggregate
* pipeline
* aggregation
* complex database processing

---

## Không để Database xử lý nặng

Không được:

* group phức tạp
* join nhiều collection
* pipeline nhiều bước
* xử lý logic trong MongoDB

---

## Phải tối ưu Query

Luôn sử dụng:

* find_one
* find
* insert_one
* update_one
* update_many
* delete_one
* delete_many
* sort
* limit
* skip
* projection

---

## Cấm

* aggregate
* pipeline
* lookup
* group
* unwind
* facet
* match phức tạp

---

## Nguyên tắc tối ưu

* Query đơn giản
* Lấy đúng field cần thiết
* Dùng projection
* Dùng index
* Không load dữ liệu dư
* Không xử lý logic trong DB
* Xử lý logic tại Service

