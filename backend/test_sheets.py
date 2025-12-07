# backend/test_sheets.py
import sys
import os

# Добавляем текущую директорию в путь, чтобы Python видел папку app
sys.path.append(os.getcwd())

from app.services.google_sheets import GoogleSheetsService

def test_connection():
    print("--- ЗАПУСК ТЕСТА GOOGLE SHEETS ---")
    
    try:
        service = GoogleSheetsService()
        
        # 1. Тест Юзеров и ПИН-кодов
        print("\n1. Загрузка пользователей...")
        users = service.get_users()
        print(f"✅ Найдено пользователей: {len(users)}")
        if users:
            print(f"   Пример: {users[0].name} (ПИН: {users[0].pin_code})")
        else:
            print("⚠️ Пользователи не найдены. Проверьте название листа 'users'!")

        # 2. Тест Машин (Новый формат)
        print("\n2. Загрузка оборудования...")
        machines = service.get_machines()
        print(f"✅ Найдено машин: {len(machines)}")
        if machines:
            print(f"   Пример: {machines[0].name} (ID: {machines[0].id}, Тип: {machines[0].type_allowed})")
        else:
            print("⚠️ Машины не найдены. Проверьте название листа 'machines'!")

        # 3. Тест Брендов
        print("\n3. Загрузка брендов...")
        brands = service.get_brands()
        print(f"✅ Найдено брендов: {len(brands)}")
        if brands:
            print(f"   Пример: {brands[0].brand_name}")
            
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        print("Совет: Проверьте, что service_account.json лежит в папке backend/")

if __name__ == "__main__":
    test_connection()