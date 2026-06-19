from django.contrib import admin
from .models import StaffProfile, StaffExperience, StaffDocument


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'user', 'department', 'position', 'contract_type', 'is_active']
    list_filter = ['department', 'contract_type', 'is_active']
    search_fields = ['employee_id', 'user__first_name', 'user__last_name']


admin.site.register(StaffExperience)
admin.site.register(StaffDocument)
