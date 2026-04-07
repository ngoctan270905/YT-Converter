# API Development Rules

## Vai trò

Đây
là
tầng ** API ** nơi
định
nghĩa ** Router, Endpoint
và
Dependency ** trong
hệ
thống.

API
là
tầng
giao
tiếp
giữa ** Client
và
Service **.

API
có
nhiệm
vụ:

*định
nghĩa
router
*định
nghĩa
endpoint
*khai
báo
dependency
*gọi
service
*nhận
dữ
liệu
từ
request
*trả
response
về
client
*sử
dụng
UnifiedResponse
để
chuẩn
hóa
response

API ** không
xử
lý
business
logic **.

---

# Nguyên tắc bắt buộc

*API
chỉ
làm
nhiệm
vụ
nhận
request
và
trả
response
*API
không
xử
lý
logic
nghiệp
vụ
*API
không
thao
tác
database
*API
không
gọi
repository
*API
chỉ
gọi
Service
*API
phải
sử
dụng
Dependency
Injection
*API
phải
dùng
UnifiedResponse

---

# Cấu trúc API

API
sẽ
làm
việc
với:

*Router
*Endpoint
*Dependency
*Service

Flow
chuẩn:

Client → API → Service → Repository → Database

Database → Repository → Service → API → Client

---

# Dependency Injection

Phải
viết
dependency
để
cung
cấp
Service
cho
Endpoint.

Service
sẽ
được
inject
thông
qua
Depends.

---

## Ví dụ Dependency

```python


async def get_attribute_service(
        db=Depends(get_database)
) -> AttributeService:
    attribute_repo = AttributeRepository(
        collection=db["attributes"]
    )

    return AttributeService(
        attribute_repository=attribute_repo
    )


```

---

# Nguyên tắc Dependency

*Dependency
phải
trả
Service
*Không
trả
Repository
*Không
trả
Database
*Không
trả
Collection
*Endpoint
chỉ
nhận
Service

---

# Endpoint Rules

Endpoint
phải:

*sử
dụng
router
*sử
dụng
response_model
*sử
dụng
status_code
*có
summary
*có
description
*có
dependency
auth
nếu
cần
*gọi
service
*trả
UnifiedResponse

---

# UnifiedResponse bắt buộc

Tất
cả
endpoint
phải
sử
dụng:

UnifiedResponse

---

## Response Model

Phải
khai
báo:

```python
response_model = UnifiedResponse[Schema]
```

---

# Ví dụ Endpoint

```python


@router.get(
    "/attributes",
    response_model=UnifiedResponse[AttributeListAll],
    status_code=status.HTTP_200_OK,
    summary="Lấy tất cả thuộc tính",
    description="Truy xuất danh sách tất cả các thuộc tính sản phẩm.",
    dependencies=[Depends(get_admin_user)]
)
async def get_all_attributes(
        attribute_service: AttributeService = Depends(get_attribute_service),
):
    attributes = await attribute_service.get_all_attributes()

    return UnifiedResponse(
        success=True,
        message="Lấy danh sách thuộc tính thành công",
        data=attributes
    )


```

---

# Nguyên tắc Endpoint

Endpoint
phải:

*nhận
service
từ
dependency
*gọi
service
*không
xử
lý
logic
*không
xử
lý
database
*không
validate
phức
tạp
*không
xử
lý
business
rule
*chỉ
gọi
service
và
trả
response

---

# Cấm

*gọi
repository
trong
API
*gọi
database
trong
API
*viết
logic
nghiệp
vụ
trong
API
*xử
lý
dữ
liệu
phức
tạp
trong
API
*vòng
lặp
xử
lý
logic
*viết
code
nặng
trong
API

---

# Phải dùng

*Depends
*Router
*Endpoint
*Service
*UnifiedResponse
*status_code
*response_model
*summary
*description

---

# Response Structure

Tất
cả
response
phải
theo
chuẩn:

```json
{
    "success": true,
    "message": "Thông báo",
    "data": {}
}
```

---



# Quy tắc đặt tên

Dependency:

get_attribute_service

Endpoint:

get_all_attributes

create_attribute

update_attribute

delete_attribute

---

# Auth Dependency

Nếu
cần
quyền
admin:

```python
dependencies = [Depends(get_admin_user)]
```

Nếu
user:

```python
dependencies = [Depends(get_current_user)]
```


