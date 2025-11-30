import os
import yaml
from ultralytics import YOLO
from django.conf import settings
from django.core.files import File
from .models import Annotation, DetectionResult
from PIL import Image
import shutil
import random


class YOLOTrainer:
    def __init__(self, ml_model):
        self.ml_model = ml_model
        self.dataset = ml_model.dataset
        self.model = None


    def debug_annotations(self):
        """Глубокая отладка аннотаций с учетом нормализованных координат"""
        print("=== ГЛУБОКАЯ ДИАГНОСТИКА АННОТАЦИЙ ===")

        all_annotations = Annotation.objects.filter(image__dataset=self.dataset)
        print(f"Всего аннотаций в БД: {all_annotations.count()}")

        if all_annotations.count() == 0:
            print("❌ Нет аннотаций в базе данных!")
            return False

        # Анализируем каждую аннотацию
        valid_annotations = 0
        invalid_annotations = []

        for i, ann in enumerate(all_annotations):
            print(f"\n--- Аннотация {i + 1} ---")
            print(f"  Изображение: {ann.image.original_filename}")
            print(f"  Метка: {ann.label}")
            print(f"  Координаты (нормализованные): x={ann.x}, y={ann.y}, width={ann.width}, height={ann.height}")

            # Проверяем существование изображения
            if not os.path.exists(ann.image.image.path):
                print("  ❌ Изображение не найдено!")
                invalid_annotations.append(ann)
                continue

            # Получаем размеры изображения
            try:
                with Image.open(ann.image.image.path) as img:
                    img_width, img_height = img.size
                print(f"  Размер изображения: {img_width}x{img_height}")

                # Пересчитываем в пиксели для проверки
                x_min_px = ann.x * img_width
                y_min_px = ann.y * img_height
                x_max_px = (ann.x + ann.width) * img_width
                y_max_px = (ann.y + ann.height) * img_height

                print(f"  BBOX в пикселях: ({x_min_px:.1f}, {y_min_px:.1f}) -> ({x_max_px:.1f}, {y_max_px:.1f})")

                # Проверяем границы в пикселях
                if (x_min_px < 0 or y_min_px < 0 or
                        x_max_px > img_width or y_max_px > img_height):
                    print(f"  ❌ BBOX выходит за границы изображения!")
                    invalid_annotations.append(ann)
                    continue

                if ann.width <= 0 or ann.height <= 0:
                    print(f"  ❌ Нулевые или отрицательные размеры BBOX!")
                    invalid_annotations.append(ann)
                    continue

                # Ключевое исправление: координаты УЖЕ нормализованы!
                # YOLO формат использует нормализованные координаты центра
                x_center = ann.x + ann.width / 2.0
                y_center = ann.y + ann.height / 2.0
                width_norm = ann.width
                height_norm = ann.height

                print(
                    f"  YOLO формат (нормализованный): class_id, {x_center:.6f}, {y_center:.6f}, {width_norm:.6f}, {height_norm:.6f}")

                # Проверяем валидность YOLO координат
                if (0 <= x_center <= 1 and 0 <= y_center <= 1 and
                        0 < width_norm <= 1 and 0 < height_norm <= 1):
                    valid_annotations += 1
                    print("  ✅ Валидная аннотация")
                else:
                    print(f"  ❌ Невалидные YOLO координаты!")
                    invalid_annotations.append(ann)

            except Exception as e:
                print(f"  ❌ Ошибка при обработке: {e}")
                invalid_annotations.append(ann)

        print(f"\n=== ИТОГИ ДИАГНОСТИКИ ===")
        print(f"Валидные аннотации: {valid_annotations}")
        print(f"Невалидные аннотации: {len(invalid_annotations)}")

        if valid_annotations == 0:
            print("❌ НЕТ ВАЛИДНЫХ АННОТАЦИЙ ДЛЯ ОБУЧЕНИЯ!")
            return False

        return True

    def prepare_yolo_dataset(self):
        """Подготовка данных в формате YOLO с учетом нормализованных координат"""
        try:
            dataset_dir = os.path.join(settings.MEDIA_ROOT, 'yolo_datasets', f'dataset_{self.dataset.id}')
            print(f"Создаем dataset в: {dataset_dir}")

            # Очищаем предыдущие данные
            if os.path.exists(dataset_dir):
                print("Очищаем предыдущую версию dataset")
                shutil.rmtree(dataset_dir)

            # Создаем структуру папок
            train_images_dir = os.path.join(dataset_dir, 'images', 'train')
            train_labels_dir = os.path.join(dataset_dir, 'labels', 'train')
            val_images_dir = os.path.join(dataset_dir, 'images', 'val')
            val_labels_dir = os.path.join(dataset_dir, 'labels', 'val')

            for dir_path in [train_images_dir, train_labels_dir, val_images_dir, val_labels_dir]:
                os.makedirs(dir_path, exist_ok=True)
                print(f"Создана директория: {dir_path}")

            # Собираем все изображения с аннотациями
            images_with_annotations = []
            classes = set()

            print("Сбор изображений с аннотациями...")
            for image in self.dataset.imagefile_set.all():
                annotations = Annotation.objects.filter(image=image)
                if annotations.exists():
                    images_with_annotations.append((image, annotations))
                    for ann in annotations:
                        classes.add(ann.label)
                    print(f"  {image.original_filename}: {annotations.count()} аннотаций")

            if not images_with_annotations:
                raise ValueError("Не найдено ни одного изображения с аннотациями")

            print(f"Всего изображений с аннотаций: {len(images_with_annotations)}")
            print(f"Классы: {sorted(classes)}")

            # Разделяем на train/val
            random.shuffle(images_with_annotations)
            split_idx = int(0.8 * len(images_with_annotations))
            train_images = images_with_annotations[:split_idx]
            val_images = images_with_annotations[split_idx:]

            # Гарантируем минимум 1 изображение в валидации
            if not val_images and train_images:
                val_images = [train_images.pop()]

            print(f"Разделение: {len(train_images)} train, {len(val_images)} val")

            # Обрабатываем тренировочные данные
            train_stats = self._process_split_corrected(train_images, train_images_dir, train_labels_dir, classes,
                                                        "train")

            # Обрабатываем валидационные данные
            val_stats = self._process_split_corrected(val_images, val_images_dir, val_labels_dir, classes, "val")

            # Финальная проверка
            if train_stats['images'] == 0:
                raise ValueError("Нет данных для обучения после обработки")

            # Создаем dataset.yaml для YOLO
            dataset_yaml = {
                'path': str(dataset_dir),
                'train': 'images/train',
                'val': 'images/val',
                'nc': len(classes),
                'names': {i: name for i, name in enumerate(sorted(classes))}
            }

            yaml_path = os.path.join(dataset_dir, 'dataset.yaml')
            with open(yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(dataset_yaml, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

            print("=== ФИНАЛЬНАЯ СТАТИСТИКА ДАННЫХ ===")
            print(f"Тренировочные данные: {train_stats['images']} изображений, {train_stats['annotations']} аннотаций")
            print(f"Валидационные данные: {val_stats['images']} изображений, {val_stats['annotations']} аннотаций")
            print(f"Всего классов: {len(classes)}")
            print(f"YAML файл: {yaml_path}")

            return yaml_path, len(classes), len(images_with_annotations)

        except Exception as e:
            if 'dataset_dir' in locals() and os.path.exists(dataset_dir):
                shutil.rmtree(dataset_dir, ignore_errors=True)
            raise Exception(f"Ошибка подготовки данных YOLO: {str(e)}")

    def _process_split_corrected(self, images_data, images_dir, labels_dir, classes, split_name):
        """Обработка с правильным учетом нормализованных координат"""
        total_annotations = 0
        processed_images = 0

        print(f"Обработка {split_name} данных (исправленные координаты)...")

        for image, annotations in images_data:
            try:
                img_path = image.image.path
                if not os.path.exists(img_path):
                    print(f"Пропускаем отсутствующее изображение: {img_path}")
                    continue

                img_filename = os.path.basename(img_path)
                dest_img_path = os.path.join(images_dir, img_filename)

                # Копируем изображение
                if not os.path.exists(dest_img_path):
                    shutil.copy2(img_path, dest_img_path)

                # Создаем файл разметки
                label_filename = os.path.splitext(img_filename)[0] + '.txt'
                label_path = os.path.join(labels_dir, label_filename)

                annotation_count = 0
                with open(label_path, 'w') as f:
                    for ann in annotations:
                        try:
                            x_center = ann.x + ann.width / 2.0
                            y_center = ann.y + ann.height / 2.0
                            width_norm = ann.width
                            height_norm = ann.height

                            # Проверяем валидность координат
                            if (0 <= x_center <= 1 and 0 <= y_center <= 1 and
                                    0 < width_norm <= 1 and 0 < height_norm <= 1 and
                                    width_norm > 0.01 and height_norm > 0.01):  # Минимальный размер 1%

                                class_idx = sorted(classes).index(ann.label)
                                f.write(
                                    f"{class_idx} {x_center:.6f} {y_center:.6f} {width_norm:.6f} {height_norm:.6f}\n")
                                annotation_count += 1
                                print(
                                    f"  ✅ Аннотация: {x_center:.3f}, {y_center:.3f}, {width_norm:.3f}, {height_norm:.3f}")
                            else:
                                print(f"  ❌ Пропущена аннотация в {img_filename}: невалидные координаты")
                                print(
                                    f"     x_center={x_center:.3f}, y_center={y_center:.3f}, width={width_norm:.3f}, height={height_norm:.3f}")

                        except Exception as e:
                            print(f"  ❌ Ошибка обработки аннотации: {e}")
                            continue

                if annotation_count > 0:
                    processed_images += 1
                    total_annotations += annotation_count
                    print(f"  ✅ {img_filename}: {annotation_count} аннотаций")
                else:
                    # Удаляем изображение без аннотаций
                    if os.path.exists(dest_img_path):
                        os.remove(dest_img_path)
                    if os.path.exists(label_path):
                        os.remove(label_path)
                    print(f"  ❌ Удалено: {img_filename} (нет валидных аннотаций)")

            except Exception as e:
                print(f"Ошибка обработки изображения {image.original_filename}: {e}")
                continue

        print(f"{split_name}: обработано {processed_images} изображений, {total_annotations} аннотаций")
        return {'images': processed_images, 'annotations': total_annotations}

    def _get_training_config(self, num_images, num_classes):
        """
        Определяет конфигурацию обучения в зависимости от объема данных и количества классов

        ПАМЯТКА ПО ПАРАМЕТРАМ ОБУЧЕНИЯ:

        МАЛЕНЬКИЙ ДАТАСЕТ (< 100 изображений):
          - epochs: 50-100 (больше эпох для компенсации малого количества данных)
          - imgsz: 640 (стандартный размер для лучшего качества)
          - batch: 4-8 (меньше батчи из-за ограниченности данных)
          - lr0: 0.01 (стандартная скорость обучения)
          - augment: True (активная аугментация для увеличения разнообразия)
          - patience: 20 (больше терпения для маленьких датасетов)

        СРЕДНИЙ ДАТАСЕТ (100-500 изображений):
          - epochs: 100-150
          - imgsz: 640
          - batch: 8-16
          - lr0: 0.01
          - augment: True
          - patience: 30

        БОЛЬШОЙ ДАТАСЕТ (> 500 изображений):
          - epochs: 150-300
          - imgsz: 640
          - batch: 16-32
          - lr0: 0.01
          - augment: True (можно уменьшить аугментацию)
          - patience: 50

        МАЛО КЛАССОВ (1-3 класса):
          - epochs: можно уменьшить на 20%
          - lr0: стандартная

        МНОГО КЛАССОВ (> 10 классов):
          - epochs: увеличить на 30-50%
          - lr0: можно уменьшить до 0.005 для стабильности
          - augment: обязательно True
        """

        # Базовые параметры
        config = {
            'epochs': 100,
            'imgsz': 640,
            'batch': 16,
            'lr0': 0.01,
            'augment': True,
            'patience': 30,
            'optimizer': 'auto',
            'weight_decay': 0.0005,
            'momentum': 0.937,
            'warmup_epochs': 3,
            'warmup_momentum': 0.8,
            'box': 7.5,  # weight for box loss
            'cls': 0.5,  # weight for class loss
            'dfl': 1.5,  # weight for dfl loss
        }

        # Адаптация под объем данных
        if num_images < 100:
            # Малый датасет
            config.update({
                'epochs': 80,
                'batch': max(4, min(8, num_images // 10)),  # адаптивный batch
                'patience': 20,
                'augment': True,  # важна активная аугментация
                'lr0': 0.01,
                'close_mosaic': 10,  # раннее отключение mosaic для стабильности
            })
        elif num_images < 500:
            # Средний датасет
            config.update({
                'epochs': 120,
                'batch': max(8, min(16, num_images // 30)),
                'patience': 30,
                'augment': True,
            })
        else:
            # Большой датасет
            config.update({
                'epochs': 150,
                'batch': max(16, min(32, num_images // 50)),
                'patience': 50,
                'augment': True,
            })

        # Адаптация под количество классов
        if num_classes <= 3:
            # Мало классов - можно обучать быстрее
            config['epochs'] = max(50, int(config['epochs'] * 0.8))
        elif num_classes > 10:
            # Много классов - нужно больше времени
            config['epochs'] = int(config['epochs'] * 1.3)
            config['lr0'] = 0.005  # более низкая LR для стабильности
            config['patience'] = int(config['patience'] * 1.2)

        print(f"⚙️  Конфигурация обучения для {num_images} изображений, {num_classes} классов:")
        print(f"   Epochs: {config['epochs']}")
        print(f"   Batch: {config['batch']}")
        print(f"   Image size: {config['imgsz']}")
        print(f"   Learning rate: {config['lr0']}")
        print(f"   Patience: {config['patience']}")

        return config

    def train_model(self):
        """Обучение YOLO модели без отслеживания прогресса"""
        try:
            print("=== НАЧАЛО ПОДГОТОВКИ ДАННЫХ ===")

            # Сначала выполняем глубокую диагностику
            if not self.debug_annotations():
                raise ValueError("Обнаружены критические проблемы с аннотациями")

            # Подготавливаем датасет
            yaml_path, num_classes, num_images = self.prepare_yolo_dataset()

            if num_images == 0:
                raise ValueError("Нет изображений с аннотациями для обучения")

            print(f"=== НАЧАЛО ОБУЧЕНИЯ ===")
            print(f"Классы: {num_classes}")
            print(f"Изображения: {num_images}")
            print(f"YAML: {yaml_path}")

            if not os.path.exists(yaml_path):
                raise FileNotFoundError(f"YAML файл не найден: {yaml_path}")

            # Настройка конфигурации обучения
            training_config = self._get_training_config(num_images, num_classes)

            print("Загружаем модель YOLO...")
            self.model = YOLO('yolov8n.pt')

            # Базовая конфигурация обучения
            training_params = {
                'data': yaml_path,
                'epochs': training_config['epochs'],
                'batch': training_config['batch'],
                'imgsz': training_config['imgsz'],
                'patience': training_config['patience'],
                'save': True,
                'exist_ok': True,
                'pretrained': True,
                'verbose': True,
                'project': os.path.join(settings.MEDIA_ROOT, 'yolo_training'),
                'name': f'model_{self.ml_model.id}',
                'lr0': training_config['lr0'],
                'optimizer': training_config['optimizer'],
                'weight_decay': training_config['weight_decay'],
                'momentum': training_config['momentum'],
                'warmup_epochs': training_config['warmup_epochs'],
                'warmup_momentum': training_config['warmup_momentum'],
                'box': training_config['box'],
                'cls': training_config['cls'],
                'dfl': training_config['dfl'],
                'augment': training_config['augment'],
            }

            if 'close_mosaic' in training_config:
                training_params['close_mosaic'] = training_config['close_mosaic']

            print("Начинаем обучение...")

            # Запускаем обучение
            results = self.model.train(**training_params)

            # Сохраняем лучшую модель
            best_model_path = os.path.join(
                settings.MEDIA_ROOT, 'yolo_training', f'model_{self.ml_model.id}', 'weights', 'best.pt'
            )

            if os.path.exists(best_model_path):
                print(f"Сохранение модели: {best_model_path}")
                with open(best_model_path, 'rb') as f:
                    self.ml_model.model_file.save(f'model_{self.ml_model.id}.pt', File(f))

                print("✅ Обучение завершено успешно!")

                # Сохраняем метрики
                if hasattr(results, 'results_dict') and results.results_dict:
                    training_results = results.results_dict
                    self.ml_model.accuracy = training_results.get('metrics/mAP50(B)', 0)
                    self.ml_model.precision = training_results.get('metrics/precision(B)', 0)
                    self.ml_model.recall = training_results.get('metrics/recall(B)', 0)
                    self.ml_model.f1_score = training_results.get('metrics/f1(B)', 0)

                    print(f"📊 Финальные метрики:")
                    print(f"  mAP50: {self.ml_model.accuracy:.3f}")
                    print(f"  Precision: {self.ml_model.precision:.3f}")
                    print(f"  Recall: {self.ml_model.recall:.3f}")
                    print(f"  F1: {self.ml_model.f1_score:.3f}")
                else:
                    self.ml_model.accuracy = 0.5
                    self.ml_model.precision = 0.5
                    self.ml_model.recall = 0.5
                    self.ml_model.f1_score = 0.5

                self.ml_model.save()

            # Очистка временных файлов
            temp_dataset_dir = os.path.join(settings.MEDIA_ROOT, 'yolo_datasets', f'dataset_{self.dataset.id}')
            if os.path.exists(temp_dataset_dir):
                print(f"Очистка временных файлов: {temp_dataset_dir}")
                shutil.rmtree(temp_dataset_dir, ignore_errors=True)

            return True

        except Exception as e:
            print(f"❌ Ошибка обучения: {str(e)}")
            import traceback
            traceback.print_exc()
            self.ml_model.training_log = f"Ошибка: {str(e)}"
            self.ml_model.save()
            return False


class YOLODetector:
    def __init__(self, ml_model):
        self.ml_model = ml_model
        self.model = None
        self.load_model()

    def load_model(self):
        """Загрузка обученной модели"""
        try:
            if self.ml_model.model_file and os.path.exists(self.ml_model.model_file.path):
                self.model = YOLO(self.ml_model.model_file.path)
                print("Модель успешно загружена")
                print(f"Доступные классы: {self.model.names}")
            else:
                raise ValueError("Файл модели не найден или модель не обучена")
        except Exception as e:
            print(f"Ошибка загрузки модели: {e}")
            raise

    def detect_image(self, image_file, confidence=0.25):
        """Детекция объектов на изображении"""
        if not self.model:
            self.load_model()

        image_path = image_file.image.path

        try:
            # Выполняем детекцию
            results = self.model.predict(
                source=image_path,
                conf=confidence,
                save=False,
                verbose=False
            )

            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is not None and len(boxes) > 0:
                    for box in boxes:
                        # Координаты bounding box
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        class_id = int(box.cls[0].cpu().numpy())

                        # Получаем имя класса
                        class_name = self.model.names.get(class_id, f'class_{class_id}')

                        detections.append({
                            'label': class_name,
                            'confidence': float(confidence),
                            'x': float(x1),
                            'y': float(y1),
                            'width': float(x2 - x1),
                            'height': float(y2 - y1),
                            'class_id': class_id
                        })

            return detections

        except Exception as e:
            print(f"Ошибка детекции: {e}")
            return []

    def detect_dataset(self, confidence=0.25):
        """Детекция объектов во всем датасете"""
        detection_count = 0

        # Удаляем старые результаты детекции
        DetectionResult.objects.filter(ml_model=self.ml_model).delete()

        for image in self.ml_model.dataset.imagefile_set.all():
            detections = self.detect_image(image, confidence)

            for detection in detections:
                DetectionResult.objects.create(
                    dataset=self.ml_model.dataset,
                    image=image,
                    ml_model=self.ml_model,
                    detected_label=detection['label'],
                    confidence=detection['confidence'],
                    x=detection['x'],
                    y=detection['y'],
                    width=detection['width'],
                    height=detection['height']
                )
                detection_count += 1

        return detection_count