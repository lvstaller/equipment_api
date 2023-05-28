import json
import re
from django.core.paginator import Paginator, EmptyPage
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from .models import EquipmentType, Equipment


def validate_serial_number(serial_number):
    equipment_types = EquipmentType.objects.all()
    template = {
        "N": r"\d",
        "A": r"[A-Z]",
        "a": r"[a-z]",
        "X": r"[A-Z\d]",
        "Z": r"[-_@]",
    }
    for equipment_type in equipment_types:
        mask = equipment_type.serial_mask

        pattern = r""
        try:
            for symbol in mask:
                pattern += template[symbol]
        except:
            continue
        if re.fullmatch(pattern, serial_number) is not None:
            return True, equipment_type.id
    return False, None


# Вывод пагинированного списка типов оборудования с возможностью поиска
@csrf_exempt
def get_equipment_type_list(request):
    # Получение параметров запроса
    search_query = request.GET.get("q", "")  # Поисковый запрос
    page_number = request.GET.get("page", 1)  # Номер страницы
    # Формирование фильтра для поиска
    filter_condition = Q(name__icontains=search_query) | Q(
        serial_mask__icontains=search_query
    )
    # Получение списка типов оборудования, отфильтрованного и отсортированного
    equipment_type_list = EquipmentType.objects.filter(filter_condition).order_by("id")
    # Создание пагинатора
    paginator = Paginator(equipment_type_list, 10)  # Показывать 10 объектов на странице
    try:
        # Получение запрошенной страницы
        page = paginator.page(page_number)
        equipment_types = page.object_list
        # Формирование данных ответа
        response_data = {
            "total_pages": paginator.num_pages,
            "current_page": page.number,
            "equipment_types": [
                {
                    "id": eq_type.id,
                    "name": eq_type.name,
                    "serial_mask": eq_type.serial_mask,
                }
                for eq_type in equipment_types
            ],
        }
        return JsonResponse(response_data)
    except EmptyPage:
        return JsonResponse({"message": "Страница не найдена"}, status=404)


def equipment_list(request):
    if request.method == "GET":
        # Получение параметров запроса
        search_query = request.GET.get("q", "")  # Поисковый запрос
        page_number = request.GET.get("page", 1)  # Номер страницы
        # Формирование фильтра для поиска
        filter_condition = Q(serial_number__icontains=search_query) | Q(
            note__icontains=search_query
        )
        # Получение списка не удаленного оборудования, отфильтрованного и отсортированного
        equipment_list = Equipment.objects.filter(
            filter_condition, is_deleted=False
        ).order_by("id")
        # Создание пагинатора
        paginator = Paginator(equipment_list, 10)  # Показывать 10 объектов на странице
        try:
            # Получение запрошенной страницы
            page = paginator.page(page_number)
            equipment = page.object_list

            # Формирование данных ответа
            response_data = {
                "total_pages": paginator.num_pages,
                "current_page": page.number,
                "equipment": [
                    {
                        "id": eq.id,
                        "equipment_type": eq.equipment_type.name,
                        "serial_number": eq.serial_number,
                        "note": eq.note,
                    }
                    for eq in equipment
                ],
            }
            return JsonResponse(response_data)
        except EmptyPage:
            return JsonResponse({"message": "Страница не найдена"}, status=404)

    elif request.method == "POST":
        data = json.loads(request.body)
        serial_numbers = data.get("serial_numbers", [])
        print(serial_numbers)
        response_data = []
        error_messages = []
        for serial_number in serial_numbers:
            # Валидация серийного номера и проверка уникальности
            status, equipment_type_id = validate_serial_number(serial_number)
            if not status:
                error_messages.append(f"Invalid serial number: {serial_number}")
            elif Equipment.objects.filter(serial_number=serial_number).exists():
                error_messages.append(f"Serial number already exists: {serial_number}")
            else:
                # Создание новой записи
                equipment = Equipment(
                    serial_number=serial_number, equipment_type_id=equipment_type_id
                )
                equipment.save()
                response_data.append(serial_number)

        return JsonResponse(
            {"equipment_ids": response_data, "errors": error_messages}, status=201
        )
    else:
        return JsonResponse({"message": "Invalid request method"}, status=400)


def equipment_detail(request, id):
    if request.method == "GET":
        # Запрос данных по id оборудования
        equipment = get_object_or_404(Equipment, id=id)
        response_data = {
            "id": equipment.id,
            "equipment_type": equipment.equipment_type.name,
            "serial_number": equipment.serial_number,
            "note": equipment.note,
            "is_deleted": equipment.is_deleted,
        }
        return JsonResponse(response_data)

    elif request.method == "PUT":
        # Редактирование записи оборудования по id
        try:
            equipment_update = Equipment.objects.get(id=id)
        except Equipment.DoesNotExist:
            return JsonResponse({"error": "Equipment not found"}, status=404)
        # Извлечение данных из тела запроса
        data = json.loads(request.body)
        # Проверка наличия полей в данных
        if "serial_number" not in data and "note" not in data:
            return JsonResponse({"error": "Missing fields"}, status=400)
        # Обновление полей оборудования
        if "serial_number" in data:
            status, equipment_type_id = validate_serial_number(data["serial_number"])
            if not status:
                JsonResponse(
                    {"error": f"Invalid serial number: {data['serial_number']}"},
                    status=400,
                )
            elif Equipment.objects.filter(serial_number=data["serial_number"]).exists():
                JsonResponse(
                    {"error": f"Serial number already exists: {data['serial_number']}"},
                    status=400,
                )
            else:
                equipment_update.serial_number = data["serial_number"]
                equipment_update.equipment_type_id = equipment_type_id
        if "note" in data:
            equipment_update.note = data["note"]
        # Сохранение обновленного оборудования
        equipment_update.save()
        return JsonResponse({"message": f"PUT request: update equipment with ID {id}"})

    elif request.method == "DELETE":
        # Удаление записи оборудования по id (мягкое удаление)
        try:
            equipment = Equipment.objects.get(id=id)
        except Equipment.DoesNotExist:
            return JsonResponse({"error": "Equipment not found"}, status=404)
        # Выполнить "мягкое удаление" (например, установить флаг удаления)
        equipment.is_deleted = True
        equipment.save()
        return JsonResponse(
            {"message": f"DELETE request: delete equipment with ID {id}"}
        )

    else:
        return JsonResponse({"message": "Invalid request method"}, status=400)
