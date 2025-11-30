document.addEventListener('DOMContentLoaded', function() {
    const image = document.getElementById('annotation-image');
    const canvas = document.getElementById('annotation-canvas');
    const ctx = canvas.getContext('2d');
    const annotationForm = document.getElementById('annotation-form');
    const annotationsList = document.getElementById('annotations-list');

    let isDrawing = false;
    let isDrawingMode = false;
    let startX, startY;
    let currentRect = null;
    let annotations = [];

    // Настройка canvas
    function setupCanvas() {
        const rect = image.getBoundingClientRect();
        canvas.width = image.offsetWidth;
        canvas.height = image.offsetHeight;
        canvas.style.width = image.offsetWidth + 'px';
        canvas.style.height = image.offsetHeight + 'px';
        canvas.style.pointerEvents = isDrawingMode ? 'auto' : 'none';

        drawAnnotations();
    }

    // Загрузка существующих аннотаций
    function loadAnnotations() {
        fetch(`/detection/api/annotations/{{ current_image.pk }}/`)
            .then(response => response.json())
            .then(data => {
                annotations = data.annotations;
                drawAnnotations();
                updateAnnotationsList();
            })
            .catch(error => console.error('Error loading annotations:', error));
    }

    // Рисование всех аннотаций
    function drawAnnotations() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Рисуем существующие аннотации
        annotations.forEach(ann => {
            drawRect(
                ann.x * canvas.width,
                ann.y * canvas.height,
                ann.width * canvas.width,
                ann.height * canvas.height,
                ann.label,
                '#00a884'
            );
        });

        // Рисуем текущий прямоугольник (если есть)
        if (currentRect) {
            drawRect(
                currentRect.x,
                currentRect.y,
                currentRect.width,
                currentRect.height,
                'Новый объект',
                '#ff6b6b'
            );
        }
    }

    // Рисование одного прямоугольника
    function drawRect(x, y, width, height, label, color) {
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, width, height);

        // Фон для подписи
        ctx.fillStyle = color;
        ctx.fillRect(x, y - 20, ctx.measureText(label).width + 10, 20);

        // Текст подписи
        ctx.fillStyle = '#ffffff';
        ctx.font = '12px Arial';
        ctx.fillText(label, x + 5, y - 5);
    }

    // Обновление списка аннотаций
    function updateAnnotationsList() {
        annotationsList.innerHTML = '';

        annotations.forEach((ann, index) => {
            const item = document.createElement('div');
            item.className = 'list-group-item d-flex justify-content-between align-items-center';
            item.setAttribute('data-annotation-id', ann.id);
            item.innerHTML = `
                <div>
                    <span class="badge badge-success mr-2">${index + 1}</span>
                    ${ann.label}
                </div>
                <button class="btn btn-sm btn-outline-danger delete-annotation" data-id="${ann.id}">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            annotationsList.appendChild(item);
        });

        // Добавляем обработчики удаления
        document.querySelectorAll('.delete-annotation').forEach(btn => {
            btn.addEventListener('click', function() {
                const annotationId = this.getAttribute('data-id');
                deleteAnnotation(annotationId);
            });
        });
    }

    // Удаление аннотации
    function deleteAnnotation(annotationId) {
        if (!confirm('Удалить эту аннотацию?')) return;

        fetch(`/detection/api/annotation/${annotationId}/delete/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                annotations = annotations.filter(ann => ann.id != annotationId);
                drawAnnotations();
                updateAnnotationsList();
                updateProgress();
            }
        })
        .catch(error => console.error('Error deleting annotation:', error));
    }

    // Сохранение аннотации
    function saveAnnotation(annotationData) {
        fetch(`/detection/api/annotation/{{ current_image.pk }}/save/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(annotationData),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                annotations.push({
                    id: data.annotation_id,
                    label: annotationData.label,
                    x: annotationData.x,
                    y: annotationData.y,
                    width: annotationData.width,
                    height: annotationData.height
                });

                drawAnnotations();
                updateAnnotationsList();
                annotationForm.reset();
                currentRect = null;
                updateProgress();

                // Показываем уведомление
                showNotification('Аннотация успешно сохранена!', 'success');
            } else {
                showNotification('Ошибка при сохранении аннотации', 'error');
                console.error('Save error:', data.errors);
            }
        })
        .catch(error => {
            console.error('Error saving annotation:', error);
            showNotification('Ошибка при сохранении', 'error');
        });
    }

    // Обновление прогресса
    function updateProgress() {
        fetch(`/detection/api/progress/{{ dataset.pk }}/`)
            .then(response => response.json())
            .then(data => {
                // Можно обновить индикатор прогресса на странице
                console.log('Progress updated:', data);
            });
    }

    // Показать уведомление
    function showNotification(message, type) {
        const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
        const notification = document.createElement('div');
        notification.className = `alert ${alertClass} alert-dismissible fade show`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="close" data-dismiss="alert">
                <span>&times;</span>
            </button>
        `;

        document.querySelector('.container').insertBefore(notification, document.querySelector('.container').firstChild);

        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    // Обработчики событий мыши
    canvas.addEventListener('mousedown', function(e) {
        if (!isDrawingMode) return;

        isDrawing = true;
        const rect = canvas.getBoundingClientRect();
        startX = e.clientX - rect.left;
        startY = e.clientY - rect.top;

        currentRect = {
            x: startX,
            y: startY,
            width: 0,
            height: 0
        };
    });

    canvas.addEventListener('mousemove', function(e) {
        if (!isDrawingMode || !isDrawing) return;

        const rect = canvas.getBoundingClientRect();
        const currentX = e.clientX - rect.left;
        const currentY = e.clientY - rect.top;

        currentRect.width = currentX - startX;
        currentRect.height = currentY - startY;

        // Обновляем отображение координат
        document.getElementById('coord-x').textContent = Math.round(currentRect.x);
        document.getElementById('coord-y').textContent = Math.round(currentRect.y);
        document.getElementById('coord-width').textContent = Math.round(Math.abs(currentRect.width));
        document.getElementById('coord-height').textContent = Math.round(Math.abs(currentRect.height));

        drawAnnotations();
    });

    canvas.addEventListener('mouseup', function() {
        if (!isDrawingMode || !isDrawing) return;

        isDrawing = false;

        // Нормализуем координаты (0-1)
        const normalizedRect = {
            x: currentRect.x / canvas.width,
            y: currentRect.y / canvas.height,
            width: Math.abs(currentRect.width) / canvas.width,
            height: Math.abs(currentRect.height) / canvas.height
        };

        // Заполняем скрытые поля формы
        document.getElementById('id_x').value = normalizedRect.x;
        document.getElementById('id_y').value = normalizedRect.y;
        document.getElementById('id_width').value = normalizedRect.width;
        document.getElementById('id_height').value = normalizedRect.height;
    });

    // Обработчик отправки формы
    annotationForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const label = document.getElementById('id_label').value;
        const x = document.getElementById('id_x').value;
        const y = document.getElementById('id_y').value;
        const width = document.getElementById('id_width').value;
        const height = document.getElementById('id_height').value;

        if (!label || !x || !y || !width || !height) {
            showNotification('Заполните все поля и нарисуйте bounding box!', 'error');
            return;
        }

        if (parseFloat(width) < 0.01 || parseFloat(height) < 0.01) {
            showNotification('Размер bounding box слишком мал!', 'error');
            return;
        }

        const annotationData = {
            label: label,
            x: parseFloat(x),
            y: parseFloat(y),
            width: parseFloat(width),
            height: parseFloat(height)
        };

        saveAnnotation(annotationData);
    });

    // Обработчик кнопки очистки
    document.getElementById('clear-canvas').addEventListener('click', function() {
        currentRect = null;
        document.getElementById('id_x').value = '';
        document.getElementById('id_y').value = '';
        document.getElementById('id_width').value = '';
        document.getElementById('id_height').value = '';
        document.getElementById('coord-x').textContent = '0';
        document.getElementById('coord-y').textContent = '0';
        document.getElementById('coord-width').textContent = '0';
        document.getElementById('coord-height').textContent = '0';
        drawAnnotations();
    });

    // Обработчик кнопки режима рисования
    document.getElementById('enable-drawing').addEventListener('click', function() {
        isDrawingMode = !isDrawingMode;
        canvas.style.pointerEvents = isDrawingMode ? 'auto' : 'none';
        this.classList.toggle('btn-primary', isDrawingMode);
        this.classList.toggle('btn-success', !isDrawingMode);
        this.innerHTML = isDrawingMode ?
            '<i class="fas fa-check"></i> Режим рисования (вкл)' :
            '<i class="fas fa-draw-polygon"></i> Режим рисования';
    });

    // Вспомогательная функция для получения CSRF токена
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Инициализация
    image.addEventListener('load', function() {
        setupCanvas();
        loadAnnotations();
    });

    // Если изображение уже загружено
    if (image.complete) {
        setupCanvas();
        loadAnnotations();
    }

    // Обработчик изменения размера окна
    window.addEventListener('resize', function() {
        setupCanvas();
    });
});