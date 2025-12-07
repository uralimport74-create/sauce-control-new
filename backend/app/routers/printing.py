import uuid
from datetime import datetime
import pytz
from fastapi import APIRouter, HTTPException
from app.models import PrintRequest
from app.services.pdf import generate_pdf_base64
from app.database import supabase # Подключение к БД

router = APIRouter()
TZ = pytz.timezone("Asia/Yekaterinburg")

@router.post("/api/print")
def api_print(req: PrintRequest):
    """Создает партию и PDF (для планшета)"""
    try:
        now = datetime.now(TZ)
        # Формируем полное название, как в старой программе
        product_full = f"{req.type} {req.category} {req.recipe} {req.brand_name} ({req.items_per_box} шт/кор.)"

        batch_id = None
        boxes = []

        # 1. Запись партии в БД
        if supabase:
            # ВАЖНО: Добавляем заглушки для полей user_name и machine_name, 
            # чтобы Supabase не ругалась на ошибку 400
            batch_data = {
                "product_info": product_full,
                "planned_quantity": req.count,
                "batch_number": req.batch_number or "",
                "user_name": "Печать на планшете", # <-- Заглушка
                "machine_name": "Не назначена"     # <-- Заглушка
            }
            
            batch_res = supabase.table("batches").insert(batch_data).execute()
            
            # Проверяем, вернулись ли данные
            if batch_res.data and len(batch_res.data) > 0:
                batch_id = batch_res.data[0]["id"]
            else:
                raise Exception("Не удалось получить ID новой партии из БД")

            # 2. Генерация ID коробок
            for _ in range(req.count):
                nid = str(uuid.uuid4())
                boxes.append({"id": nid, "batch_id": batch_id, "status": "CREATED"})
            
            # Вставляем коробки
            supabase.table("boxes").insert(boxes).execute()
        
        else:
            # Режим без БД (тестовый)
            for _ in range(req.count):
                boxes.append({"id": str(uuid.uuid4())})

        # 3. Генерация PDF
        label_data = {
            "type": req.type,
            "category": req.category,
            "recipe": req.recipe,
            "brand": req.brand_name,
            "items_per_box": req.items_per_box,
            "date": now.strftime("%d.%m.%y"),
            "time": now.strftime("%H:%M"),
        }

        pdf_b64 = generate_pdf_base64(boxes, label_data)

        return {
            "success": True,
            "batch_id": batch_id,
            "pdf_base64": pdf_b64,
            "filename": f"Batch_{batch_id or 'test'}.pdf",
        }
    except Exception as e:
        print(f"❌ ОШИБКА ПЕЧАТИ: {e}") # Пишем в консоль для отладки
        raise HTTPException(status_code=500, detail=f"Print error: {e}")