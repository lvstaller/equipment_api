from django.db import models


class EquipmentType(models.Model):
    name = models.CharField(max_length=255)
    serial_mask = models.CharField(max_length=255)


class Equipment(models.Model):
    equipment_type = models.ForeignKey(EquipmentType, on_delete=models.CASCADE)
    serial_number = models.CharField(max_length=255, unique=True)
    note = models.CharField(max_length=255, blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
