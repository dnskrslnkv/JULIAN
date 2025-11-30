# reports/utils.py
import json
import csv
from io import BytesIO
from reportlab.lib.pagesizes import  A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT

import os
from PIL import Image as PILImage, ImageDraw


# Регистрация шрифтов для поддержки кириллицы
def register_fonts():
    """Регистрация кириллических шрифтов"""
    try:
        # Попробуем найти шрифты в системе
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        ]

        for font_path in font_paths:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('DejaVu', font_path))
                return 'DejaVu'

        # Если системные шрифты не найдены, используем стандартные
        pdfmetrics.registerFont(TTFont('Helvetica', 'Helvetica'))
        return 'Helvetica'

    except Exception as e:
        print(f"Ошибка регистрации шрифтов: {e}")
        return 'Helvetica'


# Регистрируем шрифты при импорте
CYRILLIC_FONT = register_fonts()


class ReportExporter:
    def __init__(self, report):
        self.report = report
        self.styles = getSampleStyleSheet()

        # Создаем стили с кириллическими шрифтами и компактным оформлением
        self._create_compact_styles()

    def _create_compact_styles(self):
        """Создание компактных стилей с поддержкой кириллицы"""
        # Основной компактный стиль
        self.styles.add(ParagraphStyle(
            name='CompactNormal',
            parent=self.styles['Normal'],
            fontName=CYRILLIC_FONT,
            fontSize=9,
            leading=10,
            spaceAfter=6,
        ))

        # Заголовки с уменьшенными отступами
        self.styles.add(ParagraphStyle(
            name='CompactHeading1',
            parent=self.styles['Heading1'],
            fontName=CYRILLIC_FONT,
            fontSize=14,
            leading=16,
            spaceAfter=8,
            textColor=colors.HexColor('#1a365d')
        ))

        self.styles.add(ParagraphStyle(
            name='CompactHeading2',
            parent=self.styles['Heading2'],
            fontName=CYRILLIC_FONT,
            fontSize=12,
            leading=14,
            spaceAfter=6,
            textColor=colors.HexColor('#2d3748')
        ))

        self.styles.add(ParagraphStyle(
            name='CompactHeading3',
            parent=self.styles['Heading3'],
            fontName=CYRILLIC_FONT,
            fontSize=10,
            leading=12,
            spaceAfter=4,
            textColor=colors.HexColor('#4a5568')
        ))

        # Стиль для текста в таблицах с переносом слов
        self.styles.add(ParagraphStyle(
            name='TableText',
            parent=self.styles['Normal'],
            fontName=CYRILLIC_FONT,
            fontSize=8,
            leading=9,
            wordWrap='CJK',  # Изменено на CJK для лучшего переноса
            alignment=TA_LEFT,
        ))

    def _create_safe_table(self, data, colWidths, style):
        """Безопасное создание таблицы с обработкой ошибок"""
        try:
            table = Table(data, colWidths=colWidths)
            table.setStyle(style)
            return table
        except Exception as e:
            print(f"Ошибка при создании таблицы: {e}")
            # Возвращаем простую таблицу с сообщением об ошибке
            error_data = [['Ошибка отображения данных']]
            error_table = Table(error_data, colWidths=[sum(colWidths)])
            error_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.red),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            return error_table

    def _create_compact_training_parameters_section(self):
        """Компактная секция параметров обучения"""
        elements = []

        title = Paragraph("Параметры обучения", self.styles['CompactHeading2'])
        elements.append(title)
        elements.append(Spacer(1, 4))

        # Данные параметров с использованием Paragraph для переноса
        training_data = [
            [Paragraph('Параметр', self.styles['TableText']),
             Paragraph('Значение', self.styles['TableText']),
             Paragraph('Описание', self.styles['TableText'])],
            [Paragraph('Количество эпох', self.styles['TableText']),
             Paragraph(str(getattr(self.report, 'training_epochs', 'N/A')), self.styles['TableText']),
             Paragraph('Количество полных проходов через весь набор данных', self.styles['TableText'])],
            [Paragraph('Размер батча', self.styles['TableText']),
             Paragraph(str(getattr(self.report, 'training_batch_size', 'N/A')), self.styles['TableText']),
             Paragraph('Количество изображений, обрабатываемых за один шаг', self.styles['TableText'])],
            [Paragraph('Размер изображения', self.styles['TableText']),
             Paragraph(
                 f"{getattr(self.report, 'training_img_size', 'N/A')}x{getattr(self.report, 'training_img_size', 'N/A')}",
                 self.styles['TableText']),
             Paragraph('Размер, к которому масштабируются изображения', self.styles['TableText'])]
        ]

        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a202c')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), CYRILLIC_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ])

        training_table = self._create_safe_table(training_data, [1.2 * inch, 0.8 * inch, 2.5 * inch], table_style)
        elements.append(training_table)
        elements.append(Spacer(1, 12))

        return elements

    def _create_compact_metrics_help_section(self):
        """Компактная секция справки по метрикам"""
        elements = []

        title = Paragraph("Метрики качества", self.styles['CompactHeading2'])
        elements.append(title)
        elements.append(Spacer(1, 4))

        help_data = [
            [Paragraph('Метрика', self.styles['TableText']), Paragraph('Описание', self.styles['TableText'])],
            [Paragraph('Accuracy', self.styles['TableText']),
             Paragraph('Общая доля правильных предсказаний среди всех сделанных', self.styles['TableText'])],
            [Paragraph('Precision', self.styles['TableText']),
             Paragraph('Доля правильно обнаруженных объектов среди всех обнаруженных', self.styles['TableText'])],
            [Paragraph('Recall', self.styles['TableText']),
             Paragraph('Доля правильно обнаруженных объектов среди всех реальных объектов', self.styles['TableText'])],
            [Paragraph('F1-Score', self.styles['TableText']),
             Paragraph('Среднее гармоническое между Precision и Recall', self.styles['TableText'])],
        ]

        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a202c')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), CYRILLIC_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
        ])

        help_table = self._create_safe_table(help_data, [1.2 * inch, 3.3 * inch], table_style)
        elements.append(help_table)
        elements.append(Spacer(1, 12))

        return elements

    def _create_compact_high_confidence_section(self):
        """Компактная секция изображений с высокой уверенностью"""
        elements = []

        # Безопасное получение изображений
        try:
            high_conf_images = getattr(self.report, 'reportimage_set', None)
            if high_conf_images:
                high_conf_images = high_conf_images.all()[:4]  # Ограничиваем 4 изображениями для надежности
            else:
                high_conf_images = []
        except Exception as e:
            print(f"Ошибка получения изображений: {e}")
            high_conf_images = []

        if high_conf_images:
            title = Paragraph("Лучшие результаты", self.styles['CompactHeading2'])
            elements.append(title)
            elements.append(Spacer(1, 4))

            info_text = Paragraph(
                f"Показано {len(high_conf_images)} изображений с высокой уверенностью",
                self.styles['CompactNormal']
            )
            elements.append(info_text)
            elements.append(Spacer(1, 6))

            # Создаем миниатюры в две колонки
            images_data = []
            current_row = []

            for i, report_image in enumerate(high_conf_images):
                try:
                    img_with_bbox = self._create_image_with_bbox(report_image)
                    if img_with_bbox:
                        # Создаем миниатюру изображения
                        img_element = Image(img_with_bbox, width=2.2 * inch, height=1.6 * inch)

                        # Создаем подпись
                        label = getattr(report_image, 'label', 'Неизвестно')
                        confidence = getattr(report_image, 'confidence', 0)
                        caption = Paragraph(
                            f"{label} ({confidence:.1%})",
                            self.styles['CompactHeading3']
                        )

                        # Объединяем изображение и подпись в одну ячейку
                        image_cell = [[img_element], [caption]]
                        image_table = Table(image_cell)
                        image_table.setStyle(TableStyle([
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('LEFTPADDING', (0, 0), (-1, -1), 2),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                        ]))

                        current_row.append(image_table)

                        # Каждые 2 изображения создаем новую строку
                        if len(current_row) == 2:
                            images_data.append(current_row)
                            current_row = []

                except Exception as e:
                    print(f"Ошибка обработки изображения: {e}")
                    continue

            # Добавляем оставшиеся изображения
            if current_row:
                # Дополняем строку до 2 элементов пустыми ячейками
                while len(current_row) < 2:
                    current_row.append(Spacer(1, 1))
                images_data.append(current_row)

            if images_data:
                try:
                    images_table = Table(images_data, colWidths=[2.5 * inch, 2.5 * inch])
                    images_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 4),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ]))
                    elements.append(images_table)
                except Exception as e:
                    print(f"Ошибка создания таблицы изображений: {e}")
                    error_msg = Paragraph("Ошибка при отображении изображений", self.styles['CompactNormal'])
                    elements.append(error_msg)

        return elements

    def _create_image_with_bbox(self, report_image):
        """Создание изображения с bounding box для отчета"""
        try:
            img_path = getattr(report_image.image, 'image', None)
            if not img_path or not hasattr(img_path, 'path'):
                return None

            original_img = PILImage.open(img_path.path)
            img_with_bbox = original_img.copy()
            draw = ImageDraw.Draw(img_with_bbox)

            # Безопасное получение координат
            detection = getattr(report_image, 'detection', None)
            if detection:
                bbox = [
                    getattr(detection, 'x', 0),
                    getattr(detection, 'y', 0),
                    getattr(detection, 'x', 0) + getattr(detection, 'width', 0),
                    getattr(detection, 'y', 0) + getattr(detection, 'height', 0)
                ]
            else:
                # Если нет detection, используем дефолтные координаты
                width, height = original_img.size
                bbox = [width * 0.1, height * 0.1, width * 0.9, height * 0.9]

            draw.rectangle(bbox, outline='red', width=2)

            label = getattr(report_image, 'label', 'Объект')
            confidence = getattr(report_image, 'confidence', 0)
            label_text = f"{label} ({confidence:.1%})"

            text_bbox = [bbox[0], max(0, bbox[1] - 15), bbox[0] + 150, bbox[1]]
            draw.rectangle(text_bbox, fill='red')
            draw.text((bbox[0] + 3, text_bbox[1] + 2), label_text, fill='white')

            temp_buffer = BytesIO()
            img_with_bbox.save(temp_buffer, format='JPEG', quality=80)
            temp_buffer.seek(0)
            return temp_buffer

        except Exception as e:
            print(f"Ошибка создания изображения с bbox: {e}")
            return None

    def _create_stats_section(self):
        """Создание секции статистики с безопасным доступом к данным"""
        elements = []

        stats_title = Paragraph("Ключевые метрики", self.styles['CompactHeading2'])
        elements.append(stats_title)
        elements.append(Spacer(1, 4))

        # Безопасное получение данных
        total_images = getattr(self.report, 'total_images', 0)
        annotated_images = getattr(self.report, 'annotated_images', 0)
        total_annotations = getattr(self.report, 'total_annotations', 0)
        total_detections = getattr(self.report, 'total_detections', 0)
        high_confidence_detections = getattr(self.report, 'high_confidence_detections', 0)
        accuracy = getattr(self.report, 'accuracy', 0)

        # Расчет прогресса с проверкой деления на ноль
        progress = 0
        if total_images > 0:
            progress = (annotated_images / total_images) * 100

        # Основные метрики - левая колонка
        stats_left = [
            [Paragraph('Всего изображений:', self.styles['TableText']),
             Paragraph(f"{total_images:,}", self.styles['TableText'])],
            [Paragraph('Размеченных:', self.styles['TableText']),
             Paragraph(f"{annotated_images:,}", self.styles['TableText'])],
            [Paragraph('Всего аннотаций:', self.styles['TableText']),
             Paragraph(f"{total_annotations:,}", self.styles['TableText'])],
            [Paragraph('Всего обнаружений:', self.styles['TableText']),
             Paragraph(f"{total_detections:,}", self.styles['TableText'])],
        ]

        # Дополнительные метрики - правая колонка
        stats_right = [
            [Paragraph('Высокоуверенные:', self.styles['TableText']),
             Paragraph(f"{high_confidence_detections:,}", self.styles['TableText'])],
            [Paragraph('Прогресс:', self.styles['TableText']), Paragraph(f"{progress:.1f}%", self.styles['TableText'])],
            [Paragraph('Точность:', self.styles['TableText']), Paragraph(f"{accuracy:.1%}", self.styles['TableText'])],
        ]

        # Добавляем дополнительные метрики если они есть
        additional_metrics = []
        precision = getattr(self.report, 'precision', None)
        recall = getattr(self.report, 'recall', None)
        f1_score = getattr(self.report, 'f1_score', None)

        if precision is not None:
            additional_metrics.append([Paragraph('Precision:', self.styles['TableText']),
                                       Paragraph(f"{precision:.3f}", self.styles['TableText'])])
        if recall is not None:
            additional_metrics.append(
                [Paragraph('Recall:', self.styles['TableText']), Paragraph(f"{recall:.3f}", self.styles['TableText'])])
        if f1_score is not None:
            additional_metrics.append([Paragraph('F1 Score:', self.styles['TableText']),
                                       Paragraph(f"{f1_score:.3f}", self.styles['TableText'])])

        # Создаем таблицы для колонок
        col_width = 2.2 * inch
        cell_widths = [col_width * 0.6, col_width * 0.4]

        stats_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ])

        stats_table_left = self._create_safe_table(stats_left, cell_widths, stats_style)
        stats_table_right = self._create_safe_table(stats_right, cell_widths, stats_style)

        # Объединяем в две колонки
        stats_combined = [[stats_table_left, stats_table_right]]

        if additional_metrics:
            stats_additional = self._create_safe_table(additional_metrics, cell_widths, stats_style)
            stats_combined.append([stats_additional])

        stats_layout = self._create_safe_table(stats_combined, [col_width, col_width], TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        elements.append(stats_layout)
        elements.append(Spacer(1, 10))

        return elements

    def export_pdf(self):
        """Экспорт отчета в PDF с современным компактным дизайном"""
        buffer = BytesIO()

        try:
            # Компактные отступы страницы
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                topMargin=0.4 * inch,
                bottomMargin=0.4 * inch,
                leftMargin=0.3 * inch,
                rightMargin=0.3 * inch
            )
            story = []

            # Заголовок отчета
            title_text = getattr(self.report, 'title', 'Без названия')
            title = Paragraph(f"Отчет анализа: {title_text}", self.styles['CompactHeading1'])
            story.append(title)
            story.append(Spacer(1, 6))

            # Информация об отчете в компактной таблице
            info_data = [
                [Paragraph('Датасет:', self.styles['TableText']),
                 Paragraph(str(getattr(self.report.dataset, 'name', 'N/A')), self.styles['TableText'])],
                [Paragraph('ML Модель:', self.styles['TableText']),
                 Paragraph(str(getattr(self.report.ml_model, 'name', 'N/A')), self.styles['TableText'])],
                [Paragraph('Формат:', self.styles['TableText']),
                 Paragraph(str(getattr(self.report, 'get_format_display', lambda: 'N/A')()), self.styles['TableText'])],
                [Paragraph('Создан:', self.styles['TableText']),
                 Paragraph(getattr(self.report, 'created_at', 'N/A').strftime("%d.%m.%Y %H:%M"),
                           self.styles['TableText'])],
                [Paragraph('Пользователь:', self.styles['TableText']),
                 Paragraph(str(getattr(self.report.user, 'username', 'N/A')), self.styles['TableText'])]
            ]

            info_table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ])

            info_table = self._create_safe_table(info_data, [1.0 * inch, 4.5 * inch], info_table_style)
            story.append(info_table)
            story.append(Spacer(1, 10))

            # Статистика
            story.extend(self._create_stats_section())

            # Параметры обучения (только если они есть)
            if hasattr(self.report, 'training_epochs'):
                story.extend(self._create_compact_training_parameters_section())

            # Изображения с высокой уверенностью
            story.extend(self._create_compact_high_confidence_section())

            # Справка по метрикам
            story.extend(self._create_compact_metrics_help_section())

            doc.build(story)

        except Exception as e:
            print(f"Критическая ошибка при создании PDF: {e}")
            # Создаем простой PDF с сообщением об ошибке
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            story = []
            story.append(Paragraph("Ошибка при создании отчета", self.styles['CompactHeading1']))
            story.append(Paragraph(str(e), self.styles['CompactNormal']))
            doc.build(story)

        buffer.seek(0)
        return buffer

    # Методы export_csv и export_json остаются без изменений
    def export_csv(self):
        """Экспорт отчета в CSV"""
        buffer = BytesIO()
        writer = csv.writer(buffer)

        # Безопасный доступ к данным
        report_title = getattr(self.report, 'title', 'Без названия')
        writer.writerow(['Отчет:', report_title])
        writer.writerow([])

        # Основная информация
        writer.writerow(['Информация об отчете'])
        writer.writerow(['Датасет:', getattr(self.report.dataset, 'name', 'N/A')])
        writer.writerow(['ML Модель:', getattr(self.report.ml_model, 'name', 'N/A')])
        writer.writerow(['Формат:', getattr(self.report, 'get_format_display', lambda: 'N/A')()])
        writer.writerow(['Создан:', getattr(self.report, 'created_at', 'N/A').strftime("%d.%m.%Y %H:%M")])
        writer.writerow(['Пользователь:', getattr(self.report.user, 'username', 'N/A')])
        writer.writerow([])

        # Статистика
        writer.writerow(['Статистика'])
        writer.writerow(['Метрика', 'Значение'])
        writer.writerow(['Всего изображений', getattr(self.report, 'total_images', 0)])
        writer.writerow(['Размеченных изображений', getattr(self.report, 'annotated_images', 0)])
        writer.writerow(['Всего аннотаций', getattr(self.report, 'total_annotations', 0)])
        writer.writerow(['Всего обнаружений', getattr(self.report, 'total_detections', 0)])
        writer.writerow(['Обнаружений с уверенностью >75%', getattr(self.report, 'high_confidence_detections', 0)])
        writer.writerow(['Точность модели', f"{getattr(self.report, 'accuracy', 0):.2%}"])

        precision = getattr(self.report, 'precision', None)
        recall = getattr(self.report, 'recall', None)
        f1_score = getattr(self.report, 'f1_score', None)

        if precision is not None:
            writer.writerow(['Precision', f"{precision:.3f}"])
        if recall is not None:
            writer.writerow(['Recall', f"{recall:.3f}"])
        if f1_score is not None:
            writer.writerow(['F1 Score', f"{f1_score:.3f}"])
        writer.writerow([])

        # Параметры обучения (если есть)
        if hasattr(self.report, 'training_epochs'):
            writer.writerow(['Параметры обучения'])
            writer.writerow(['Параметр', 'Значение', 'Описание'])
            writer.writerow(['Количество эпох', getattr(self.report, 'training_epochs', 'N/A'),
                             'Количество полных проходов через весь набор данных'])
            writer.writerow(['Размер батча', getattr(self.report, 'training_batch_size', 'N/A'),
                             'Количество изображений, обрабатываемых за один шаг'])
            writer.writerow(['Размер изображения', getattr(self.report, 'training_img_size', 'N/A'),
                             'Размер, к которому масштабируются изображения'])
            writer.writerow([])

        # Изображения с высокой уверенностью
        try:
            high_conf_images = getattr(self.report, 'reportimage_set', None)
            if high_conf_images:
                high_conf_images = high_conf_images.all()
                if high_conf_images:
                    writer.writerow(['Изображения с высокой уверенностью (>75%)'])
                    writer.writerow(['Изображение', 'Метка', 'Уверенность', 'Координаты'])
                    for img in high_conf_images:
                        detection = getattr(img, 'detection', None)
                        if detection:
                            coords = f"({getattr(detection, 'x', 0):.2f}, {getattr(detection, 'y', 0):.2f}, {getattr(detection, 'width', 0):.2f}, {getattr(detection, 'height', 0):.2f})"
                        else:
                            coords = '(N/A)'

                        writer.writerow([
                            getattr(getattr(img, 'image', None), 'original_filename', 'N/A'),
                            getattr(img, 'label', 'N/A'),
                            f"{getattr(img, 'confidence', 0):.1%}",
                            coords
                        ])
        except Exception as e:
            print(f"Ошибка при экспорте изображений в CSV: {e}")

        buffer.seek(0)
        return buffer

    def export_json(self):
        """Экспорт отчета в JSON"""
        # Безопасный доступ ко всем данным
        report_data = {
            'title': getattr(self.report, 'title', 'Без названия'),
            'dataset': getattr(self.report.dataset, 'name', 'N/A'),
            'ml_model': getattr(self.report.ml_model, 'name', 'N/A'),
            'format': getattr(self.report, 'get_format_display', lambda: 'N/A')(),
            'created_at': getattr(self.report, 'created_at', 'N/A').isoformat(),
            'user': getattr(self.report.user, 'username', 'N/A'),
            'statistics': {
                'total_images': getattr(self.report, 'total_images', 0),
                'annotated_images': getattr(self.report, 'annotated_images', 0),
                'total_annotations': getattr(self.report, 'total_annotations', 0),
                'total_detections': getattr(self.report, 'total_detections', 0),
                'high_confidence_detections': getattr(self.report, 'high_confidence_detections', 0),
                'accuracy': getattr(self.report, 'accuracy', 0),
                'precision': getattr(self.report, 'precision', None),
                'recall': getattr(self.report, 'recall', None),
                'f1_score': getattr(self.report, 'f1_score', None),
            },
            'high_confidence_images': []
        }

        # Добавляем параметры обучения если они есть
        if hasattr(self.report, 'training_epochs'):
            report_data['training_parameters'] = {
                'epochs': getattr(self.report, 'training_epochs', 'N/A'),
                'batch_size': getattr(self.report, 'training_batch_size', 'N/A'),
                'image_size': getattr(self.report, 'training_img_size', 'N/A'),
                'description': {
                    'epochs': 'Количество полных проходов через весь набор данных',
                    'batch_size': 'Количество изображений, обрабатываемых за один шаг',
                    'image_size': 'Размер, к которому масштабируются изображения'
                }
            }

        # Добавляем информацию об изображениях
        try:
            high_conf_images = getattr(self.report, 'reportimage_set', None)
            if high_conf_images:
                for img in high_conf_images.all():
                    detection = getattr(img, 'detection', None)
                    image_info = {
                        'image': getattr(getattr(img, 'image', None), 'original_filename', 'N/A'),
                        'label': getattr(img, 'label', 'N/A'),
                        'confidence': getattr(img, 'confidence', 0),
                        'coordinates': {
                            'x': getattr(detection, 'x', 0) if detection else 0,
                            'y': getattr(detection, 'y', 0) if detection else 0,
                            'width': getattr(detection, 'width', 0) if detection else 0,
                            'height': getattr(detection, 'height', 0) if detection else 0
                        }
                    }
                    report_data['high_confidence_images'].append(image_info)
        except Exception as e:
            print(f"Ошибка при добавлении изображений в JSON: {e}")

        json_str = json.dumps(report_data, indent=2, ensure_ascii=False)
        buffer = BytesIO(json_str.encode('utf-8'))
        return buffer


def generate_report_file(report, format_type):
    """Генерация файла отчета с обработкой ошибок"""
    try:
        exporter = ReportExporter(report)

        if format_type == 'pdf':
            buffer = exporter.export_pdf()
            filename = f'report_{report.id}.pdf'
            content_type = 'application/pdf'
        elif format_type == 'csv':
            buffer = exporter.export_csv()
            filename = f'report_{report.id}.csv'
            content_type = 'text/csv'
        elif format_type == 'json':
            buffer = exporter.export_json()
            filename = f'report_{report.id}.json'
            content_type = 'application/json'
        else:
            raise ValueError(f"Unsupported format: {format_type}")

        return buffer, filename, content_type

    except Exception as e:
        print(f"Критическая ошибка при генерации отчета: {e}")
        # Возвращаем простой PDF с ошибкой
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph("Ошибка при создании отчета", styles['Heading1']))
        story.append(Paragraph(str(e), styles['Normal']))
        doc.build(story)
        buffer.seek(0)
        return buffer, f'error_report_{report.id}.pdf', 'application/pdf'

