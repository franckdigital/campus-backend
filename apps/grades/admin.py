from django.contrib import admin
from .models import GradeCategory, Grade, ReportCard

admin.site.register(GradeCategory)
admin.site.register(Grade)
admin.site.register(ReportCard)
