from django.urls import path
from . import views

urlpatterns = [
    path("equipment", views.equipment_list, name="equipment_list"),
    path("equipment/<int:id>", views.equipment_detail, name="equipment_detail"),
    path("equipment-type", views.get_equipment_type_list, name="equipment_types_list"),
]
