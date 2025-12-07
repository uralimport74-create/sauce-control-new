# backend/app/models.py
from typing import Optional, List
from pydantic import BaseModel

# --- Модели для данных из Google Sheets и API ---

class User(BaseModel):
    name: str
    pin_code: str
    is_active: bool = True


class Machine(BaseModel):
    id: str
    name: str
    type_allowed: str = ""
    category_allowed: str = ""
    is_active: bool = True


class Brand(BaseModel):
    # Описание продукта из таблицы brands
    brand_name: str
    type: str
    category: str
    recipe: str
    items_per_box: int
    aliases: str = ""          # Алиасы для поиска
    # Поля ниже используются только в части экранов и могут быть пустыми
    count: int = 0
    batch_number: Optional[str] = ""


class PrintRequest(BaseModel):
    # Запрос на создание партии и PDF
    brand_name: str
    type: str
    category: str
    recipe: str
    items_per_box: int
    count: int
    batch_number: Optional[str] = ""


class ScanRequest(BaseModel):
    box_id: str
    mode: str = "production"  # production / inventory / revision

    # Поля для режима фасовки
    user_name: Optional[str] = None
    machine_id: Optional[str] = None
    scanned_at_local: Optional[str] = None  # Время на устройстве (если был офлайн)
    coworkers: Optional[List[str]] = None   # Дополнительные операторы (по именам)
