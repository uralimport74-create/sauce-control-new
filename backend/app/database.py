import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
logger = logging.getLogger("Database")

# МЫ НЕ ПИШЕМ КЛЮЧИ СЮДА ЯВНО! МЫ ИСПОЛЬЗУЕМ os.getenv
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("✅ Supabase подключена")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения Supabase: {e}")
else:
    logger.warning("⚠️ SUPABASE_URL или SUPABASE_KEY не найдены в .env")