import os
import json
from typing import List, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.models import User, Machine, Brand

CREDENTIALS_FILE = "service_account.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class GoogleSheetsService:
    def __init__(self):
        self.creds = None
        self.service = None
        # ВАЖНО: Убедитесь, что тут ваш правильный ID таблицы
        self.config_sheet_id = "1fdldtl7fOCM97ZNMZS4BrePyGKPNOJkySa3bZ_Y6mfA"
        self._authenticate()

    def _authenticate(self):
        """Авторизация к Google Sheets.
        1) Сначала пробуем взять JSON из переменной окружения GOOGLE_SERVICE_ACCOUNT_JSON
        2) Если её нет — пробуем файл service_account.json рядом с backend
        """
        # 1. Пробуем переменную окружения (удобно для Railway)
        env_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        if env_json:
            try:
                info = json.loads(env_json)
                self.creds = service_account.Credentials.from_service_account_info(
                    info, scopes=SCOPES
                )
                self.service = build("sheets", "v4", credentials=self.creds)
                print("✅ Авторизация Google через переменную окружения прошла успешно")
                return
            except Exception as e:
                print(f"❌ Ошибка авторизации Google из окружения: {e}")

        # 2. Файл service_account.json (локальный запуск)
        if os.path.exists(CREDENTIALS_FILE):
            try:
                self.creds = service_account.Credentials.from_service_account_file(
                    CREDENTIALS_FILE, scopes=SCOPES
                )
                self.service = build("sheets", "v4", credentials=self.creds)
                print("✅ Авторизация Google через файл service_account.json прошла успешно")
            except Exception as e:
                print(f"❌ Ошибка авторизации Google из файла: {e}")
        else:
            print(
                f"⚠️ Файл {CREDENTIALS_FILE} не найден и переменная "
                f"GOOGLE_SERVICE_ACCOUNT_JSON не задана"
            )

    def _get_values(self, sheet_names: List[str]) -> List[List[str]]:
        """Ищет данные в одном из перечисленных листов"""
        if not self.service or not self.config_sheet_id:
            print("⚠️ _get_values: нет self.service или config_sheet_id")
            return []

        for name in sheet_names:
            range_name = f"'{name}'!A1:Z2000"
            try:
                result = (
                    self.service.spreadsheets()
                    .values()
                    .get(spreadsheetId=self.config_sheet_id, range=range_name)
                    .execute()
                )
                values = result.get("values", [])
                if values:
                    # print(f"   ℹ️ Данные найдены на листе: {name}")
                    return values
            except Exception as e:
                print(f"⚠️ Ошибка чтения листа '{name}': {e}")
                continue

        print(f"⚠️ Не удалось найти листы с именами: {sheet_names}")
        return []

    def _find_exact_col(self, header: List[str], candidates: List[str]) -> int:
        """Ищет колонку по точному совпадению или частичному, если точного нет"""
        header_lower = [str(h).lower().strip() for h in header]

        # 1. Сначала ищем точное совпадение
        for cand in candidates:
            cand_lower = cand.lower().strip()
            if cand_lower in header_lower:
                return header_lower.index(cand_lower)

        # 2. Потом допускаем частичное совпадение
        for i, col in enumerate(header_lower):
            for cand in candidates:
                cand_lower = cand.lower().strip()
                if cand_lower in col:
                    return i
        return -1

    def get_users(self) -> List[User]:
        # Ищем лист users (или brands - users)
        rows = self._get_values(["users", "brands - users", "Users", "Пользователи"])
        if not rows:
            print("get_users: не нашли ни одного листа")
            return []

        header = rows[0]
        data = rows[1:]

        # Настраиваем поиск под ваши заголовки: "Имя", "PIN", "Активен"
        idx_name = self._find_exact_col(header, ["Имя", "Name"])
        idx_pin = self._find_exact_col(header, ["PIN", "Пин", "Pin"])
        idx_active = self._find_exact_col(header, ["Активен", "Active"])

        users: List[User] = []

        for row in data:
            if idx_name == -1 or len(row) <= idx_name:
                continue

            name = row[idx_name].strip()
            if not name:
                continue

            pin = ""
            if idx_pin != -1 and len(row) > idx_pin:
                pin = str(row[idx_pin]).strip()

            is_active = True
            if idx_active != -1 and len(row) > idx_active:
                if str(row[idx_active]).lower() not in ["true", "1", "yes"]:
                    is_active = False

            if is_active:
                users.append(User(name=name, pin_code=pin))

        return users

    def get_machines(self) -> List[Machine]:
        # Ищем лист machines (или brands - machines)
        rows = self._get_values(["machines", "brands - machines", "Machine_Settings"])
        if not rows:
            print("get_machines: не нашли ни одного листа")
            return []

        header = rows[0]
        data = rows[1:]

        # Ваши заголовки: Machine_ID, Name, Types, Categories, Active
        idx_id = self._find_exact_col(header, ["Machine_ID", "ID"])
        idx_name = self._find_exact_col(header, ["Name", "Имя"])
        idx_type = self._find_exact_col(header, ["Types", "Type_Allowed", "Тип"])
        idx_cat = self._find_exact_col(header, ["Categories", "Category_Allowed"])
        idx_active = self._find_exact_col(header, ["Active", "Активен"])

        machines: List[Machine] = []

        for i, row in enumerate(data, start=2):
            if idx_name == -1 or len(row) <= idx_name:
                continue

            name = row[idx_name].strip()
            if not name:
                continue

            m_id = f"mach_{i}"
            if idx_id != -1 and len(row) > idx_id:
                val = row[idx_id].strip()
                if val:
                    m_id = val

            is_active = True
            if idx_active != -1 and len(row) > idx_active:
                if str(row[idx_active]).lower() not in ["true", "1", "yes"]:
                    is_active = False

            if is_active:
                type_allowed = (
                    row[idx_type].strip()
                    if idx_type != -1 and len(row) > idx_type
                    else ""
                )
                cat_allowed = (
                    row[idx_cat].strip()
                    if idx_cat != -1 and len(row) > idx_cat
                    else ""
                )

                machines.append(
                    Machine(
                        id=m_id,
                        name=name,
                        type_allowed=type_allowed,
                        category_allowed=cat_allowed,
                        is_active=True,
                    )
                )

        return machines

    def get_brands(self) -> List[Brand]:
        # Ищем лист brands
        rows = self._get_values(["brands", "brands - brands", "Бренды"])
        if not rows:
            print("get_brands: лист 'brands' пустой или не найден")
            return []

        header = rows[0]
        data = rows[1:]

        # Ваши заголовки: Тип, Категория, Рецептура, Бренд, кол-во шт в коробке, aliases
        # ВАЖНО: Ищем "Бренд" (короткое имя), а не "brand_1c"
        idx_brand = self._find_exact_col(header, ["Бренд", "Brand"])
        idx_type = self._find_exact_col(header, ["Тип", "Type"])
        idx_cat = self._find_exact_col(header, ["Категория", "Category"])
        idx_rec = self._find_exact_col(header, ["Рецептура", "Recipe"])
        idx_qty = self._find_exact_col(header, ["кол-во шт в коробке", "items", "qty"])
        idx_alias = self._find_exact_col(header, ["aliases", "алиасы"])

        print(
            "get_brands: индексы колонок -> "
            "idx_brand={0}, idx_type={1}, idx_cat={2}, idx_rec={3}, idx_qty={4}, idx_alias={5}".format(
                idx_brand, idx_type, idx_cat, idx_rec, idx_qty, idx_alias
            )
        )

        brands: List[Brand] = []

        for row in data:
            if idx_brand == -1 or len(row) <= idx_brand:
                continue

            b_name = str(row[idx_brand]).strip()
            if not b_name:
                continue

            qty = 0
            if idx_qty != -1 and len(row) > idx_qty:
                val = str(row[idx_qty]).strip()
                if val.isdigit():
                    qty = int(val)

            brands.append(
                Brand(
                    brand_name=b_name,
                    type=row[idx_type].strip()
                    if idx_type != -1 and len(row) > idx_type
                    else "",
                    category=row[idx_cat].strip()
                    if idx_cat != -1 and len(row) > idx_cat
                    else "",
                    recipe=row[idx_rec].strip()
                    if idx_rec != -1 and len(row) > idx_rec
                    else "",
                    items_per_box=qty,
                    aliases=row[idx_alias].strip()
                    if idx_alias != -1 and len(row) > idx_alias
                    else "",
                )
            )

        print("get_brands: загружено брендов:", len(brands))
        if brands:
            try:
                example = brands[0]
                if hasattr(example, "dict"):
                    print("get_brands: пример первой записи:", example.dict())
                elif hasattr(example, "model_dump"):
                    print("get_brands: пример первой записи:", example.model_dump())
                else:
                    print("get_brands: пример первой записи (raw):", example)
            except Exception as e:
                print("get_brands: не удалось вывести пример записи:", e)

        return brands

