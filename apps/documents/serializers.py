from rest_framework import serializers
from .models import DocumentCategory, Document, Archive, ArchiveDocument


class DocumentCategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True)

    class Meta:
        model = DocumentCategory
        fields = [
            'id', 'name', 'code', 'description', 'parent', 'parent_name',
            'allowed_extensions', 'max_file_size_mb', 'requires_validation',
            'retention_years', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DocumentSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True)
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    validated_by_name = serializers.CharField(source='validated_by.full_name', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'description', 'category', 'category_name',
            'site', 'site_name', 'academic_year', 'academic_year_name',
            'student', 'student_name', 'file', 'file_name', 'file_size',
            'file_type', 'status', 'uploaded_by', 'uploaded_by_name',
            'validated_by', 'validated_by_name', 'validated_at',
            'validation_notes', 'tags', 'metadata', 'is_active', 'created_at'
        ]
        read_only_fields = [
            'id', 'file_name', 'file_size', 'file_type',
            'validated_by', 'validated_at', 'created_at'
        ]


class DocumentListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'category', 'category_name', 'student',
            'student_name', 'file_type', 'status', 'created_at'
        ]


class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            'title', 'description', 'category', 'site', 'academic_year',
            'student', 'file', 'tags', 'metadata'
        ]


class ArchiveDocumentSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source='document.title', read_only=True)
    added_by_name = serializers.CharField(source='added_by.full_name', read_only=True)

    class Meta:
        model = ArchiveDocument
        fields = ['id', 'archive', 'document', 'document_title', 'added_at', 'added_by', 'added_by_name']
        read_only_fields = ['id', 'added_at']


class ArchiveSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    document_count = serializers.IntegerField(read_only=True)
    archive_documents = ArchiveDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Archive
        fields = [
            'id', 'name', 'description', 'site', 'site_name',
            'academic_year', 'academic_year_name', 'created_by', 'created_by_name',
            'archived_at', 'retention_until', 'document_count', 'archive_documents',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'archived_at', 'created_at']


class ArchiveListSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    document_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Archive
        fields = [
            'id', 'name', 'site', 'site_name', 'academic_year',
            'academic_year_name', 'document_count', 'archived_at'
        ]
