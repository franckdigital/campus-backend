from django.contrib import admin
from .models import Parent, Student, StudentParent, StudentFile, StudentCard


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ['get_full_name', 'get_email', 'relationship', 'profession', 'is_active']
    list_filter = ['relationship', 'is_active']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'profession']

    def get_full_name(self, obj):
        return obj.user.full_name
    get_full_name.short_description = 'Nom complet'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['matricule', 'get_full_name', 'get_email', 'site', 'status', 'is_active']
    list_filter = ['status', 'is_active', 'site', 'gender']
    search_fields = ['matricule', 'user__email', 'user__first_name', 'user__last_name']
    ordering = ['user__last_name', 'user__first_name']

    def get_full_name(self, obj):
        return obj.user.full_name
    get_full_name.short_description = 'Nom complet'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'


@admin.register(StudentParent)
class StudentParentAdmin(admin.ModelAdmin):
    list_display = ['get_student_name', 'get_parent_name', 'is_primary', 'receives_notifications']
    list_filter = ['is_primary', 'receives_notifications']
    search_fields = ['student__user__first_name', 'student__user__last_name', 'parent__user__first_name']

    def get_student_name(self, obj):
        return obj.student.user.full_name
    get_student_name.short_description = 'Étudiant'

    def get_parent_name(self, obj):
        return obj.parent.user.full_name
    get_parent_name.short_description = 'Parent'


@admin.register(StudentFile)
class StudentFileAdmin(admin.ModelAdmin):
    list_display = ['title', 'student', 'file_type', 'academic_year', 'created_by', 'created_at']
    list_filter = ['file_type', 'academic_year', 'is_active']
    search_fields = ['title', 'student__matricule', 'student__user__first_name']
    ordering = ['-created_at']


@admin.register(StudentCard)
class StudentCardAdmin(admin.ModelAdmin):
    list_display = ['card_number', 'student', 'academic_year', 'issue_date', 'expiry_date', 'is_valid']
    list_filter = ['academic_year', 'is_valid', 'is_active']
    search_fields = ['card_number', 'student__matricule', 'student__user__first_name']
    ordering = ['-issue_date']
