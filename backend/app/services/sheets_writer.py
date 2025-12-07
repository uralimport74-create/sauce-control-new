import os
from datetime import datetime
import pytz
from google.oauth2 import service_account
from googleapiclient.discovery import build

CREDENTIALS_FILE = "service_account.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
REPORTS_SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID_REPORTS")
TZ = pytz.timezone("Asia/Yekaterinburg")

def get_service():
    if not os.path.exists(CREDENTIALS_FILE):
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES
        )
        return build("sheets", "v4", credentials=creds)
    except:
        return None

def write_report(data: dict):
    if not REPORTS_SPREADSHEET_ID:
        print("GS LOG: Нет ID таблицы отчетов")
        return

    service = get_service()
    if not service:
        return

    try:
        now = datetime.now(TZ)
        sheet_title = now.strftime("%d.%m.%Y")

        spreadsheet = service.spreadsheets().get(spreadsheetId=REPORTS_SPREADSHEET_ID).execute()
        sheets = spreadsheet.get('sheets', [])
        sheet_id = None
        
        for s in sheets:
            if s['properties']['title'] == sheet_title:
                sheet_id = s['properties']['sheetId']
                break
        
        if sheet_id is None:
            req_body = { "requests": [{ "addSheet": { "properties": {"title": sheet_title} } }] }
            service.spreadsheets().batchUpdate(spreadsheetId=REPORTS_SPREADSHEET_ID, body=req_body).execute()
            headers = ["Время", "Бренд", "Тип", "Категория", "Рецепт", "Кол-во (факт)", "Партия №", "ID Партии"]
            service.spreadsheets().values().append(
                spreadsheetId=REPORTS_SPREADSHEET_ID,
                range=f"'{sheet_title}'!A1",
                valueInputOption="RAW",
                body={"values": [headers]}
            ).execute()

        row = [
            data.get("time_str", ""),
            data.get("brand", ""),
            data.get("type", ""),
            data.get("category", ""),
            data.get("recipe", ""),
            data.get("count", 0),
            data.get("batch_num", ""),
            data.get("batch_id", "")
        ]

        service.spreadsheets().values().append(
            spreadsheetId=REPORTS_SPREADSHEET_ID,
            range=f"'{sheet_title}'!A1",
            valueInputOption="RAW",
            body={"values": [row]}
        ).execute()
        
    except Exception as e:
        print(f"GS WRITE ERROR: {e}")