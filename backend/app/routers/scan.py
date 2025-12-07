from datetime import datetime
import pytz
from fastapi import APIRouter, HTTPException, Body
from app.models import ScanRequest
from app.database import supabase
from app.services.telegram import send_message
from app.services.sheets_writer import write_report

router = APIRouter()
TZ = pytz.timezone("Asia/Yekaterinburg")

@router.post("/api/scan")
def api_scan(req: ScanRequest):
    """Единая точка входа для сканирования"""
    if not supabase:
        return {"status": "error", "message": "Нет БД"}

    try:
        # 1. Ищем коробку
        res = supabase.table("boxes").select("*").eq("id", req.box_id).execute()
        if not res.data:
            return {"status": "error", "message": "НЕИЗВЕСТНЫЙ КОД"}

        box = res.data[0]
        batch_id = box.get("batch_id")
        now = datetime.now(TZ)

        # --- РЕЖИМ 1: ПРОИЗВОДСТВО (ФАСОВКА) ---
                # --- РЕЖИМ 1: ПРОИЗВОДСТВО (ФАСОВКА) ---
        if req.mode == "production":
            if box.get("status") == "PRODUCED":
                return {"status": "error", "message": "ДУБЛЬ! Коробка уже была"}

            # Проверка плана (опционально, можно отключить)
            if batch_id:
                # Получаем план партии
                b_res = supabase.table("batches").select("planned_quantity").eq("id", batch_id).execute()
                planned = b_res.data[0]["planned_quantity"] if b_res.data else 0
                # Считаем факт
                cnt_res = supabase.table("boxes").select("id", count="exact").eq("batch_id", batch_id).eq("status", "PRODUCED").execute()
                produced = cnt_res.count or 0
                
                if produced >= planned:
                    return {"status": "warning", "message": "План партии выполнен!"}

            # Пишем, кто и когда сделал + доп. сотрудники
            coworkers = req.coworkers or []
            update_data = {
                "status": "PRODUCED",
                "scanned_at": req.scanned_at_local or now.isoformat(),
                "scanned_by_user_name": req.user_name,
                "produced_on_machine_id": req.machine_id,
                "coworkers": coworkers,
            }
            supabase.table("boxes").update(update_data).eq("id", req.box_id).execute()
            return {"status": "success", "message": "✅ ОК"}

            # Пишем, кто и когда сделал
            update_data = {
                "status": "PRODUCED",
                "scanned_at": req.scanned_at_local or now.isoformat(),
                "scanned_by_user_name": req.user_name,
                "produced_on_machine_id": req.machine_id
            }
            supabase.table("boxes").update(update_data).eq("id", req.box_id).execute()
            return {"status": "success", "message": "✅ ОК"}

        # --- РЕЖИМ 2: ИНВЕНТАРИЗАЦИЯ ---
        elif req.mode == "inventory":
            # Просто обновляем статус инвентаризации
            supabase.table("boxes").update(
                {"status": "INVENTORY_OK", "inventory_at": now.isoformat()}
            ).eq("id", req.box_id).execute()
            
            # Узнаем имя продукта для отображения
            prod_name = "Неизвестный продукт"
            if batch_id:
                b = supabase.table("batches").select("product_info").eq("id", batch_id).execute()
                if b.data: prod_name = b.data[0].get("product_info")
            
            return {"status": "success", "product": prod_name}

        # --- РЕЖИМ 3: ПРОВЕРКА (РЕВИЗОР) ---
        elif req.mode == "revision":
            # Ничего не пишем, только читаем
            batch_info = {}
            if batch_id:
                b = supabase.table("batches").select("*").eq("id", batch_id).execute()
                if b.data: batch_info = b.data[0]
            
            return {
                "status": "success",
                "box": box,
                "batch": batch_info
            }

    except Exception as e:
        print(f"SCAN ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ... (Остальные функции api_finish, api_finish_inventory оставляем или добавляем ниже)
@router.post("/api/finish")
def api_finish(payload: dict = Body(...)):
    # (Код из прошлого сообщения для завершения партии)
    try:
        count = payload.get("count_done", 0)
        brand_name = payload.get("brand_name", "???")
        text = f"✅ <b>Готовая продукция</b>\n\n📦 {brand_name}\n🔢 {count} кор.\n👤 {payload.get('user_name', '')}"
        send_message(text)
        
        gs_data = {
            "time_str": datetime.now(TZ).strftime("%H:%M:%S"),
            "brand": brand_name,
            "count": count,
            "batch_num": payload.get("batch_number", ""),
            "batch_id": payload.get("batch_id", "")
        }
        write_report(gs_data)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/finish_inventory")
def api_finish_inventory(payload: dict = Body(...)):
    stats = payload.get("stats", {})
    if not stats: return {"success": True}
    
    lines = [f"{name} — {qty} кор." for name, qty in stats.items()]
    text = f"📋 <b>Инвентаризация завершена</b>\nВсего: {sum(stats.values())}\n\n" + "\n".join(lines)
    send_message(text)
    return {"success": True}