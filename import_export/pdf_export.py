# -*- coding: utf-8 -*-
"""
Модуль для экспорта отчетов в PDF формат.
Содержит функции для генерации различных форм и отчетов.
"""
from io import BytesIO
from datetime import datetime
from urllib.parse import quote
from flask import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from collections import defaultdict


def _setup_fonts():
    """Настраивает шрифты для PDF документов."""
    # Регистрируем шрифт Times New Roman (или Liberation Serif как аналог)
    # Пытаемся найти системный шрифт с кириллицей (Times New Roman или аналог)
    times_font_paths = [
        '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ]
    
    # Ищем доступный шрифт (приоритет Serif, затем Sans)
    regular_font_path = None
    bold_font_path = None
    
    # Сначала ищем Serif (Times New Roman аналог)
    for path in times_font_paths:
        if os.path.exists(path) and 'Serif' in path and 'Regular' in path:
            regular_font_path = path
            break
    
    # Если не нашли Serif, ищем Sans
    if not regular_font_path:
        for path in times_font_paths:
            if os.path.exists(path) and ('Regular' in path or ('Sans.ttf' in path and 'Bold' not in path and 'Serif' not in path)):
                regular_font_path = path
                break
    
    # Ищем Bold версию
    for path in times_font_paths:
        if os.path.exists(path) and 'Bold' in path:
            # Предпочитаем Serif Bold, если есть
            if 'Serif' in path:
                bold_font_path = path
                break
            elif not bold_font_path:  # Сохраняем первый найденный Bold
                bold_font_path = path
    
    # Регистрируем шрифты, если найдены
    if regular_font_path:
        try:
            pdfmetrics.registerFont(TTFont('TimesFont', regular_font_path))
            font_name = 'TimesFont'
        except:
            font_name = 'Helvetica'
    else:
        font_name = 'Helvetica'
    
    if bold_font_path:
        try:
            pdfmetrics.registerFont(TTFont('TimesFontBold', bold_font_path))
            bold_font_name = 'TimesFontBold'
        except:
            bold_font_name = 'Helvetica-Bold'
    else:
        bold_font_name = 'Helvetica-Bold'
    
    return font_name, bold_font_name


def generate_form8_pdf(department, equipment_list, org_name, mol_name, db_session, models):
    """
    Генерирует PDF файл формы 8 (Книга учета материальных ценностей) для отдела.
    
    Args:
        department: Объект Department
        equipment_list: Список объектов Equipment
        org_name: Название организации
        mol_name: Имя МОЛ
        db_session: SQLAlchemy сессия для запросов
        models: Модуль models с моделями (Nome, Vendor, Users, Knt, Invoices, InvoiceEquipment)
    
    Returns:
        Response объект Flask с PDF файлом
    """
    if not equipment_list:
        raise ValueError("Список ТМЦ пуст")
    
    # Настраиваем шрифты
    font_name, bold_font_name = _setup_fonts()
    
    # Создаем буфер для PDF
    buffer = BytesIO()
    
    # Создаем документ в альбомной ориентации
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                           rightMargin=10*mm, leftMargin=10*mm,
                           topMargin=10*mm, bottomMargin=10*mm)
    
    # Контейнер для элементов документа
    elements = []
    
    # Стили
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor('#000000'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName=bold_font_name
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#000000'),
        alignment=TA_LEFT,
        fontName=font_name
    )
    
    table_data_style = ParagraphStyle(
        'TableData',
        parent=styles['Normal'],
        fontSize=6,
        textColor=colors.HexColor('#000000'),
        alignment=TA_CENTER,
        fontName=font_name,
        leading=7
    )
    
    table_number_style = ParagraphStyle(
        'TableNumber',
        parent=styles['Normal'],
        fontSize=6,
        textColor=colors.HexColor('#000000'),
        alignment=TA_CENTER,
        fontName=font_name,
        leading=7
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontSize=6,
        textColor=colors.HexColor('#000000'),
        alignment=TA_CENTER,
        fontName=bold_font_name,
        leading=7
    )
    
    # Титульная страница
    elements.append(Spacer(1, 20*mm))
    form_title = Paragraph('Форма № 8', normal_style)
    elements.append(form_title)
    elements.append(Spacer(1, 5*mm))
    
    # Основной заголовок
    main_title = Paragraph('КНИГА № ____<br/>УЧЕТА МАТЕРИАЛЬНЫХ ЦЕННОСТЕЙ', title_style)
    elements.append(main_title)
    elements.append(Spacer(1, 10*mm))
    
    # Информация об отделе и датах
    info_data = [
        [
            Paragraph('Учреждение:', normal_style),
            Paragraph(org_name, normal_style),
            Paragraph('по ОКУД', normal_style),
            Paragraph('', normal_style)
        ],
        [
            Paragraph('Структурное подразделение:', normal_style),
            Paragraph(department.name, normal_style),
            Paragraph('Дата открытия', normal_style),
            Paragraph('', normal_style)
        ],
        [
            Paragraph('Материально ответственное лицо:', normal_style),
            Paragraph(mol_name, normal_style),
            Paragraph('Дата закрытия', normal_style),
            Paragraph('', normal_style)
        ],
        [
            Paragraph('', normal_style),
            Paragraph('', normal_style),
            Paragraph('по ОКПО', normal_style),
            Paragraph('', normal_style)
        ]
    ]
    
    info_table = Table(info_data, colWidths=[50*mm, 90*mm, 35*mm, 25*mm])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), bold_font_name),
        ('FONTNAME', (1, 0), (1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10*mm))
    
    # Даты начала и окончания
    date_text = f'Начата «____» ________ {datetime.now().year} г.<br/>Окончена «____» ________ {datetime.now().year} г.'
    date_para = Paragraph(date_text, normal_style)
    elements.append(date_para)
    elements.append(Spacer(1, 5*mm))
    elements.append(PageBreak())
    
    # Пояснения к форме
    explanations = [
        'Пояснения к форме:',
        '1. Книга используется для учета материальных ценностей, выданных в установленных случаях во временное пользование на период не более одного месяца.',
        '2. Книга ведется в подразделении, на складе, в мастерской (цехе) воинской части.',
        '3. В книге отдельные листы отводятся для каждого наименования материальных ценностей или для каждой единицы (военнослужащего), получающей их.',
    ]
    
    for exp in explanations:
        elements.append(Paragraph(exp, normal_style))
        elements.append(Spacer(1, 3*mm))
    
    elements.append(PageBreak())
    
    # Группируем ТМЦ по nomeid (группам ТМЦ)
    equipment_by_nome = defaultdict(list)
    for eq in equipment_list:
        equipment_by_nome[eq.nomeid].append(eq)
    
    # Для каждой группы ТМЦ создаем отдельную страницу
    for nome_id, nome_equipment_list in equipment_by_nome.items():
        # Получаем название группы ТМЦ
        nome = db_session.query(models.Nome).get(nome_id)
        nome_name = nome.name if nome else f'Группа ID {nome_id}'
        
        # Создаем единую таблицу для всей страницы
        first_eq = nome_equipment_list[0] if nome_equipment_list else None
        
        def safe_str(value):
            """Безопасное преобразование в строку, возвращает '' если None"""
            return str(value) if value is not None else ''
        
        warehouse = safe_str(first_eq.places.name) if first_eq and first_eq.places else ''
        rack = safe_str(getattr(first_eq, 'warehouse_rack', None)) if first_eq else ''
        cell = safe_str(getattr(first_eq, 'warehouse_cell', None)) if first_eq else ''
        unit_name = safe_str(getattr(first_eq, 'unit_name', None)) if first_eq else ''
        unit_code = safe_str(getattr(first_eq, 'unit_code', None)) if first_eq else ''
        price = f"{float(first_eq.cost):,.2f}".replace(',', ' ') if first_eq and first_eq.cost else ''
        
        brand = ''
        if first_eq and first_eq.nome and first_eq.nome.vendorid:
            vendor = db_session.query(models.Vendor).get(first_eq.nome.vendorid)
            brand = safe_str(vendor.name) if vendor else ''
        
        category = ''
        if first_eq and first_eq.nome and first_eq.nome.category_sort:
            category = str(first_eq.nome.category_sort)
        profile = safe_str(getattr(first_eq, 'profile', None)) if first_eq else ''
        size = safe_str(getattr(first_eq, 'size', None)) if first_eq else ''
        stock_norm = safe_str(getattr(first_eq, 'stock_norm', None)) if first_eq else ''
        service_life = first_eq.dtendlife.strftime('%d.%m.%Y') if first_eq and first_eq.dtendlife else ''
        
        # Создаем единую таблицу
        table_data = []
        
        # Первая строка - заголовки верхней секции
        header_row1 = [
            Paragraph('Склад', table_header_style),
            Paragraph('Стеллаж', table_header_style),
            Paragraph('Ячейка', table_header_style),
            Paragraph('Единица измерения', table_header_style),
            Paragraph('', table_header_style),
            Paragraph('Цена, руб. коп.', table_header_style),
            Paragraph('Марка', table_header_style),
            Paragraph('Категория (сорт)', table_header_style),
            Paragraph('Профиль', table_header_style),
            Paragraph('Размер', table_header_style),
            Paragraph('Норма запаса', table_header_style),
            Paragraph('Срок службы', table_header_style)
        ]
        table_data.append(header_row1)
        
        # Вторая строка - подзаголовки
        header_row2 = [
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('наименование', table_header_style),
            Paragraph('код', table_header_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style)
        ]
        table_data.append(header_row2)
        
        # Третья строка - все данные из базы данных
        data_row3 = [
            Paragraph(warehouse, table_data_style) if warehouse else Paragraph('', table_data_style),
            Paragraph(rack, table_data_style) if rack else Paragraph('', table_data_style),
            Paragraph(cell, table_data_style) if cell else Paragraph('', table_data_style),
            Paragraph(unit_name, table_data_style) if unit_name else Paragraph('', table_data_style),
            Paragraph(unit_code, table_data_style) if unit_code else Paragraph('', table_data_style),
            Paragraph(price, table_data_style) if price else Paragraph('', table_data_style),
            Paragraph(brand, table_data_style) if brand else Paragraph('', table_data_style),
            Paragraph(category, table_data_style) if category else Paragraph('', table_data_style),
            Paragraph(profile, table_data_style) if profile else Paragraph('', table_data_style),
            Paragraph(size, table_data_style) if size else Paragraph('', table_data_style),
            Paragraph(stock_norm, table_data_style) if stock_norm else Paragraph('', table_data_style),
            Paragraph(service_life, table_data_style) if service_life else Paragraph('', table_data_style)
        ]
        table_data.append(data_row3)
        
        # Четвертая строка - "Наименование материальных ценностей"
        nome_row = [
            Paragraph(f'Наименование материальных ценностей "{nome_name}"', table_header_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style)
        ]
        table_data.append(nome_row)
        
        # Пятая строка - заголовки основной таблицы
        main_header_row1 = [
            Paragraph('Порядковый<br/>номер<br/>записи', table_header_style),
            Paragraph('Дата<br/>записи', table_header_style),
            Paragraph('Документ', table_header_style),
            Paragraph('Документ', table_header_style),
            Paragraph('Документ', table_header_style),
            Paragraph('От кого получено<br/>(кому отпущено)', table_header_style),
            Paragraph('Заводской номер<br/>(иной номер)', table_header_style),
            Paragraph('Инвентарный<br/>номер', table_header_style),
            Paragraph('Приход', table_header_style),
            Paragraph('Расход', table_header_style),
            Paragraph('Остаток', table_header_style),
            Paragraph('Контроль<br/>(подпись и дата)', table_header_style)
        ]
        table_data.append(main_header_row1)
        
        # Шестая строка - подзаголовки для документа
        main_header_row2 = [
            Paragraph('', table_header_style),
            Paragraph('', table_header_style),
            Paragraph('наименование', table_header_style),
            Paragraph('дата', table_header_style),
            Paragraph('номер', table_header_style),
            Paragraph('', table_header_style),
            Paragraph('', table_header_style),
            Paragraph('', table_header_style),
            Paragraph('', table_header_style),
            Paragraph('', table_header_style),
            Paragraph('', table_header_style),
            Paragraph('', table_header_style)
        ]
        table_data.append(main_header_row2)
        
        # Данные для этой группы
        total_cost = 0
        for idx, eq in enumerate(nome_equipment_list, 1):
            date_str = eq.datepost.strftime('%d.%m.%Y') if eq.datepost else ''
            
            doc_name = 'Поступление'
            doc_date = date_str
            doc_number = ''
            
            # Пытаемся найти первую накладную для этого ТМЦ
            invoice_eq = db_session.query(models.InvoiceEquipment).join(
                models.Invoices
            ).filter(
                models.InvoiceEquipment.equipment_id == eq.id
            ).order_by(models.Invoices.invoice_date.asc()).first()
            
            if invoice_eq and invoice_eq.invoice:
                doc_name = 'Накладная'
                doc_date = invoice_eq.invoice.invoice_date.strftime('%d.%m.%Y') if invoice_eq.invoice.invoice_date else date_str
                doc_number = invoice_eq.invoice.invoice_number or ''
                
                invoice = invoice_eq.invoice
                from_info = ''
                
                if invoice.type == 'Склад-МОЛ':
                    if invoice.from_knt_id:
                        knt = db_session.query(models.Knt).get(invoice.from_knt_id)
                        if knt and knt.name:
                            from_info = knt.name
                        else:
                            from_info = f'Склад ID {invoice.from_knt_id}'
                    else:
                        from_info = 'Склад (не указан)'
                elif invoice.type == 'МОЛ-МОЛ':
                    if invoice.from_user_id:
                        from_user = db_session.query(models.Users).get(invoice.from_user_id)
                        if from_user and from_user.login:
                            from_info = from_user.login
                        else:
                            from_info = f'МОЛ ID {invoice.from_user_id}'
                    else:
                        from_info = 'МОЛ (не указан)'
                elif invoice.type == 'МОЛ-Склад':
                    if invoice.from_user_id:
                        from_user = db_session.query(models.Users).get(invoice.from_user_id)
                        if from_user and from_user.login:
                            from_info = from_user.login
                        else:
                            from_info = f'МОЛ ID {invoice.from_user_id}'
                    else:
                        from_info = 'МОЛ (не указан)'
                else:
                    from_info = 'Не указано'
                
                from_to_info = from_info
            else:
                mol_name = eq.users.login if eq.users else 'Не указан'
                from_to_info = mol_name
            
            factory_num = eq.sernum or ''
            inv_num = eq.invnum or ''
            
            cost = float(eq.cost) if eq.cost else 0.0
            total_cost += cost
            receipt = f"{cost:,.2f}".replace(',', ' ') if cost > 0 else ''
            expense = ''
            balance = receipt
            
            row = [
                Paragraph(str(idx), table_data_style),
                Paragraph(date_str, table_data_style) if date_str else '',
                Paragraph(doc_name, table_data_style) if doc_name else '',
                Paragraph(doc_date, table_data_style) if doc_date else '',
                Paragraph(doc_number, table_data_style) if doc_number else '',
                Paragraph(from_to_info, table_data_style) if from_to_info else '',
                Paragraph(factory_num, table_data_style) if factory_num else '',
                Paragraph(inv_num, table_data_style) if inv_num else '',
                Paragraph(receipt, table_number_style) if receipt else '',
                Paragraph(expense, table_number_style) if expense else '',
                Paragraph(balance, table_number_style) if balance else '',
                Paragraph('', table_data_style)
            ]
            table_data.append(row)
        
        # Итоговая строка для этой группы
        total_cost_str = f"{total_cost:,.2f}".replace(',', ' ')
        total_row = [
            Paragraph('ИТОГО', table_header_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph(total_cost_str, table_number_style),
            Paragraph('', table_data_style),
            Paragraph(total_cost_str, table_number_style),
            Paragraph('', table_data_style)
        ]
        table_data.append(total_row)
        
        # Создаем таблицу
        table = Table(table_data, colWidths=[
            15*mm, 18*mm, 22*mm, 18*mm, 18*mm, 40*mm, 22*mm, 20*mm, 20*mm, 20*mm, 20*mm, 28*mm
        ])
        
        # Стиль единой таблицы
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('FONTNAME', (0, 0), (-1, 0), bold_font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 6),
            ('SPAN', (3, 0), (4, 0)),
            ('FONTSIZE', (0, 1), (-1, 1), 6),
            ('FONTNAME', (3, 1), (4, 1), bold_font_name),
            ('SPAN', (0, 0), (0, 1)),
            ('SPAN', (1, 0), (1, 1)),
            ('SPAN', (2, 0), (2, 1)),
            ('SPAN', (5, 0), (5, 1)),
            ('SPAN', (6, 0), (6, 1)),
            ('SPAN', (7, 0), (7, 1)),
            ('SPAN', (8, 0), (8, 1)),
            ('SPAN', (9, 0), (9, 1)),
            ('SPAN', (10, 0), (10, 1)),
            ('SPAN', (11, 0), (11, 1)),
            ('FONTSIZE', (0, 2), (-1, 2), 6),
            ('FONTNAME', (0, 3), (-1, 3), bold_font_name),
            ('FONTSIZE', (0, 3), (-1, 3), 6),
            ('SPAN', (0, 3), (-1, 3)),
            ('FONTNAME', (0, 4), (-1, 4), bold_font_name),
            ('FONTSIZE', (0, 4), (-1, 4), 6),
            ('SPAN', (2, 4), (4, 4)),
            ('FONTNAME', (0, 5), (-1, 5), font_name),
            ('FONTSIZE', (0, 5), (-1, 5), 5),
            ('FONTNAME', (0, 6), (-1, -2), font_name),
            ('FONTSIZE', (0, 6), (-1, -2), 6),
            ('ALIGN', (0, 6), (-1, -2), 'CENTER'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('FONTNAME', (0, -1), (-1, -1), bold_font_name),
            ('FONTSIZE', (0, -1), (-1, -1), 6),
        ]))
        
        elements.append(table)
        
        # Разрыв страницы перед следующей группой (кроме последней)
        nome_ids_list = list(equipment_by_nome.keys())
        if nome_id != nome_ids_list[-1]:
            elements.append(PageBreak())
    
    # Собираем PDF
    doc.build(elements)
    
    # Подготовка ответа
    buffer.seek(0)
    
    # Создаем безопасное имя файла
    safe_dept_name = department.name.replace(' ', '_').encode('ascii', 'ignore').decode('ascii')
    if not safe_dept_name:
        safe_dept_name = 'department'
    filename_ascii = f"form8_{safe_dept_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    filename_utf8 = f"form8_{department.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filename_encoded = quote(filename_utf8.encode('utf-8'))
    
    response = Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'inline; filename="{filename_ascii}"; filename*=UTF-8\'\'{filename_encoded}'
        }
    )
    
    return response

