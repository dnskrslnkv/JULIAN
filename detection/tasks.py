from celery import shared_task
from .models import MLModel, DetectionResult
from .yolo_utils import YOLOTrainer, YOLODetector


@shared_task
def train_yolo_model(model_id):
    """Задача Celery для обучения YOLO модели без отслеживания прогресса"""
    try:
        ml_model = MLModel.objects.get(id=model_id)
        ml_model.status = 'training'
        ml_model.training_log = "Модель обучается... Это может занять несколько минут."
        ml_model.save()

        # Обучаем модель
        trainer = YOLOTrainer(ml_model)
        success = trainer.train_model()

        # Обновляем статус модели
        ml_model.refresh_from_db()
        if success:
            ml_model.status = 'trained'
            ml_model.training_log = "Модель успешно обучена!"
            ml_model.save()
        else:
            ml_model.status = 'error'
            ml_model.training_log = "Ошибка обучения модели"
            ml_model.save()

        return True

    except Exception as e:
        # Обновляем статус модели в случае ошибки
        try:
            ml_model = MLModel.objects.get(id=model_id)
            ml_model.status = 'error'
            ml_model.training_log = f"Ошибка: {str(e)}"
            ml_model.save()
        except:
            pass
        raise e


@shared_task
def run_detection_task(model_id, confidence=0.25):
    """Задача Celery для запуска детекции без отслеживания прогресса"""
    try:
        ml_model = MLModel.objects.get(id=model_id)

        # Удаляем старые результаты
        DetectionResult.objects.filter(ml_model=ml_model).delete()

        # Запускаем детекцию
        detector = YOLODetector(ml_model)
        detection_count = detector.detect_dataset(confidence)

        return {
            'status': 'Детекция завершена!',
            'detection_count': detection_count,
            'model_id': ml_model.id
        }

    except Exception as e:
        raise e
