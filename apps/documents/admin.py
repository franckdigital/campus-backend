from django.contrib import admin
from .models import DocumentCategory, Document, Archive, ArchiveDocument


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'parent', 'requires_validation', 'retention_years', 'is_active']
    list_filter = ['requires_validation', 'is_active']
    search_fields = ['name', 'code']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'site', 'student', 'status', 'uploaded_by', 'created_at']
    list_filter = ['status', 'category', 'site', 'academic_year']
    search_fields = ['title', 'description', 'file_name']
    ordering = ['-created_at']


@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    list_display = ['name', 'site', 'academic_year', 'document_count', 'created_by', 'archived_at']
    list_filter = ['site', 'academic_year']
    search_fields = ['name', 'description']
    ordering = ['-archived_at']


@admin.register(ArchiveDocument)
class ArchiveDocumentAdmin(admin.ModelAdmin):
    list_display = ['archive', 'document', 'added_by', 'added_at']
    list_filter = ['archive']
    search_fields = ['document__title']
