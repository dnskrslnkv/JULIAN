import fitz
from io import BytesIO
from django.core.files import File
from .models import ImageFile


def extract_images_from_pdf(pdf_file):
    """Извлечение изображений из PDF файла"""
    try:
        # Открываем PDF файл
        pdf_document = fitz.open(pdf_file.pdf.path)
        extracted_images = []

        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]

            # Получаем изображения со страницы
            image_list = page.get_images()

            for img_index, img in enumerate(image_list):
                # Получаем изображение
                xref = img[0]
                base_image = pdf_document.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                # Создаем имя файла
                image_filename = f"{pdf_file.original_filename}_page_{page_num + 1}_img_{img_index + 1}.{image_ext}"

                # Создаем объект ImageFile
                image_file = ImageFile(
                    dataset=pdf_file.dataset,
                    original_filename=image_filename,
                    source_pdf=pdf_file,
                    page_number=page_num + 1
                )

                # Сохраняем изображение
                image_file.image_file.save(
                    image_filename,
                    File(BytesIO(image_bytes))
                )
                image_file.save()
                extracted_images.append(image_file)

        pdf_document.close()

        # Обновляем статус PDF файла
        pdf_file.images_extracted = True
        pdf_file.page_count = len(pdf_document)
        pdf_file.save()

        return extracted_images

    except Exception as e:
        print(f"Ошибка при извлечении изображений из PDF: {e}")
        return []


def extract_pdf_pages_as_images(pdf_file, dpi=150):
    """Конвертация страниц PDF в изображения"""
    try:
        pdf_document = fitz.open(pdf_file.pdf.path)
        extracted_images = []

        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]

            # Конвертируем страницу в изображение
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
            img_data = pix.tobytes("jpeg")

            # Создаем имя файла
            image_filename = f"{pdf_file.original_filename}_page_{page_num + 1}.jpg"

            # Создаем объект ImageFile
            image_file = ImageFile(
                dataset=pdf_file.dataset,
                original_filename=image_filename,
                source_pdf=pdf_file,
                page_number=page_num + 1
            )

            # Сохраняем изображение
            image_file.image_file.save(
                image_filename,
                File(BytesIO(img_data))
            )
            image_file.save()
            extracted_images.append(image_file)

        pdf_document.close()

        # Обновляем статус PDF файла
        pdf_file.images_extracted = True
        pdf_file.page_count = len(pdf_document)
        pdf_file.save()

        return extracted_images

    except Exception as e:
        print(f"Ошибка при конвертации PDF в изображения: {e}")
        return []