import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # <--- 1. НОВЫЙ ИМПОРТ
from fastapi.responses import FileResponse  # <--- 2. НОВЫЙ ИМПОРТ

from app.services.google_sheets import GoogleSheetsService
from app.database import supabase
from app.routers import printing as print_router
from app.routers import scan as scan_router

# --- НАСТРОЙКИ ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SauceControl")

sheets_service = GoogleSheetsService()

app = FastAPI(title="Sauce Control v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем API
app.include_router(print_router.router)
app.include_router(scan_router.router)

# --- API Endpoints ---
@app.get("/api/ping")
def ping():
    return {"status": "ok"}

@app.get("/api/users")
def get_users():
    return sheets_service.get_users()

@app.get("/api/machines")
def get_machines():
    return sheets_service.get_machines()

@app.get("/api/brands")
def get_brands():
    return sheets_service.get_brands()

@app.post("/api/auth/login")
def login(req: dict):
    users = sheets_service.get_users()
    user_id = req.get("user_id")
    pin_code = req.get("pin_code")
    user = next((u for u in users if u.name == user_id), None)
    if user and str(user.pin_code).strip() == str(pin_code).strip():
        return {"success": True, "user": user}
    return {"success": False, "message": "Неверный ПИН"}


# --- 3. РАЗДАЧА ФРОНТЕНДА (В САМОМ НИЗУ) ---

# Указываем путь к папке static (она должна лежать рядом с папкой app)
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

if os.path.exists(static_path):
    # Подключаем статику (картинки, скрипты)
    app.mount("/assets", StaticFiles(directory=os.path.join(static_path, "assets")), name="assets")

    # Любой другой путь возвращает index.html (для работы Vue Router)
    @app.get("/{full_path:path}")
    async def serve_vue_app(full_path: str):
        return FileResponse(os.path.join(static_path, "index.html"))
else:
    print("⚠️ Папка static не найдена. Запустите 'npm run build' и скопируйте dist в backend/static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)