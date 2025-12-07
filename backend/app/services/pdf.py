import os
import io
import base64
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics import renderPDF
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Путь к шрифтам. Поднимаемся на 3 уровня вверх от этого файла
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")

FONT_REGULAR_NAME = "DejaVu"
FONT_BOLD_NAME = "DejaVu-Bold"

def register_fonts():
    """Регистрация шрифтов"""
    try:
        regular_path = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
        bold_path = os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")

        if os.path.exists(regular_path):
            pdfmetrics.registerFont(TTFont(FONT_REGULAR_NAME, regular_path))
        else:
            print(f"⚠️ Шрифт не найден: {regular_path}")
            
        if os.path.exists(bold_path):
            pdfmetrics.registerFont(TTFont(FONT_BOLD_NAME, bold_path))
    except Exception as e:
        print(f"Ошибка шрифтов: {e}")

# Регистрируем при импорте
register_fonts()

def generate_pdf_base64(boxes_data: list, label_info: dict) -> str:
    """Генерация PDF (код перенесен из старого проекта)"""
    buffer = io.BytesIO()
    w, h = 120 * mm, 75 * mm
    c = canvas.Canvas(buffer, pagesize=(w, h))

    registered = pdfmetrics.getRegisteredFontNames()
    base_font = FONT_BOLD_NAME if FONT_BOLD_NAME in registered else "Helvetica-Bold"

    qr_size = 35 * mm
    text_left = 60 * mm
    text_right = w - 5 * mm
    max_text_width = text_right - text_left

    def fit_font_size(text: str, font_name: str, max_width: float, base_size: int, min_size: int = 8) -> int:
        size = base_size
        while size > min_size:
            width = pdfmetrics.stringWidth(text, font_name, size)
            if width <= max_width: return size
            size -= 1
        return min_size

    for idx, box in enumerate(boxes_data, start=1):
        box_id = box["id"]
        
        # Бренд
        brand = label_info["brand"]
        # Если бренд пустой, ставим заглушку, чтобы не падало
        if not brand: brand = "Бренд"
            
        brand_max_width = w - 10 * mm
        brand_size = fit_font_size(brand, base_font, brand_max_width, base_size=32, min_size=14)
        c.setFont(base_font, brand_size)
        x_brand = (w - pdfmetrics.stringWidth(brand, base_font, brand_size)) / 2
        y_brand = h - 12 * mm
        c.drawString(x_brand, y_brand, brand)

        # QR
        qr_widget = QrCodeWidget(box_id)
        bounds = qr_widget.getBounds()
        qr_w = bounds[2] - bounds[0]
        qr_h = bounds[3] - bounds[1]
        sx = qr_size / qr_w
        sy = qr_size / qr_h
        d = Drawing(qr_size, qr_size, transform=[sx, 0, 0, sy, 0, 0])
        d.add(qr_widget)
        renderPDF.draw(d, c, 8 * mm, (h - qr_size) / 2 - 5 * mm)

        # Текст
        t_type = label_info.get("type", "") or ""
        t_cat = label_info.get("category", "") or ""
        type_cat = f"{t_type} {t_cat}".strip().upper()
        
        recipe = label_info.get("recipe", "") or ""
        items = label_info.get("items_per_box", 0)
        date_str = label_info.get("date", "")
        time_str = label_info.get("time", "")

        lines = [
            (type_cat, fit_font_size(type_cat, base_font, max_text_width, 18, 12)),
            (recipe, 13),
            (f"Коробка № {idx}", 13),
            (f"Коробка: {items} шт", 12),
            (f"Изг: {date_str} {time_str}", 14)
        ]

        line_step = 7 * mm
        total_span = (len(lines) - 1) * line_step
        y = h / 2 + total_span / 2 - 5 * mm

        for txt, fsize in lines:
            c.setFont(base_font, fsize)
            width = pdfmetrics.stringWidth(txt, base_font, fsize)
            x = text_left + (max_text_width - width) / 2
            c.drawString(x, y, txt)
            y -= line_step

        c.showPage()

    c.save()
    return base64.b64encode(buffer.getvalue()).decode("utf-8")