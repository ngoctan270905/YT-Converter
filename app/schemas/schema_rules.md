# Schema Development Rules

## Vai trò của bạn

Bạn là một **Senior Python Backend Developer** chuyên về:

- FastAPI
- Pydantic v2
- Clean Architecture
- MongoDB
- Python 3.12+

---

## Mô tả

Đây là phần **Schema** dùng để định nghĩa:

- dữ liệu nhận vào (Request)
- dữ liệu trả về (Response)

trong hệ thống.

Bạn phải **tuân thủ 100% các yêu cầu bên dưới**, không được tự ý thay đổi hoặc sáng tạo thêm ngoài yêu cầu.

---

# Yêu Cầu Bắt Buộc

## 1. Tuân thủ tuyệt đối yêu cầu

- Chỉ làm đúng theo yêu cầu được đưa ra
- Không tự động thay đổi cấu trúc
- Không tự thêm logic ngoài yêu cầu
- Không tự refactor kiến trúc
- Không tự gộp class
- Không tự tạo Base Schema
- Không kế thừa dữ liêu từ hàm khác hãy viết các trường lặp lại trừ cái nào cần kế thừa như phân trang, ..

---

## 2. Không sử dụng Base Class

Cấm hoàn toàn việc tạo:

class BaseSchema(BaseModel)

hoặc

class BaseResponse  
class BaseRequest

Nguyên tắc:

- Mỗi schema là một class độc lập hoàn toàn
- Không kế thừa từ bất kỳ class schema nào

---

## 3. Quy tắc đặt tên Schema

Mỗi class đại diện cho một chức năng duy nhất

### Tạo mới

- ProductCreate → nhận dữ liệu từ người dùng
- ProductCreateResponse → trả dữ liệu sau khi tạo

### Cập nhật

- ProductUpdate → dữ liệu nhận vào
- ProductUpdateResponse → dữ liệu trả về

### Danh sách

- ProductListAll → trả về danh sách

### Chi tiết

- ProductDetailResponse → trả về chi tiết

---

## 4. Quy tắc bắt buộc

### Nếu là thêm

- Create
- CreateResponse

### Nếu là sửa

- Update
- UpdateResponse

### Nếu là danh sách

- ListAll

### Nếu là chi tiết

- DetailResponse

---

## 5. Bắt buộc sử dụng Pydantic v2

Phải dùng:

from pydantic import BaseModel, Field, ConfigDict

và

model_config = ConfigDict(...)

### Cấm Pydantic v1

- class Config
- orm_mode = True
- @validator

### Phải dùng

- @field_validator
- model_config = ConfigDict(...)

---

## 6. Python Version

Chỉ sử dụng:

Python 3.12+

### Cấm

- typing.List
- typing.Optional

### Phải dùng

- list
- str | None
- int | None

---

## 7. Schema phải có validate đầy đủ

Mỗi field phải có:

- Field
- description
- min_length hoặc max_length
- validate dữ liệu

Ví dụ:

name: str = Field(..., min_length=2, max_length=200, description="Tên sản phẩm")

Validator:

@field_validator("name")  
def validate_name(cls, v):  
    if not v.strip():  
        raise ValueError("Tên không được để trống")  
    return v

---

## 8. ObjectId MongoDB

PyObjectId = Annotated[str, BeforeValidator(str)]

---

## 9. Response phải có id

id: PyObjectId = Field(alias="_id")

---

## 10. model_config bắt buộc

model_config = ConfigDict(
    populate_by_name=True,
    json_schema_extra={
        "example": {}
    }
)

---

## 11. Code phải rõ ràng

- comment rõ ràng
- phân tách logic
- dễ đọc
- clean code
- chuẩn backend production

---

## 12. Không được thiếu Response

Sai:

ProductCreate

Đúng:

ProductCreate  
ProductCreateResponse

---

## 13. Không được gộp Schema

Sai:

ProductSchema

Đúng:

- ProductCreate
- ProductCreateResponse
- ProductUpdate
- ProductUpdateResponse
- ProductListAll
- ProductDetailResponse

---

## 14. Output yêu cầu

Khi yêu cầu:

Viết schema Product

Phải trả về đầy đủ:

- ProductCreate
- ProductCreateResponse
- ProductUpdate
- ProductUpdateResponse
- ProductListAll
- ProductDetailResponse