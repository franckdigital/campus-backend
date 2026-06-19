from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import DocumentCategory, Document, Archive, ArchiveDocument
from .serializers import (
    DocumentCategorySerializer, DocumentSerializer, DocumentListSerializer,
    DocumentUploadSerializer, ArchiveSerializer, ArchiveListSerializer,
    ArchiveDocumentSerializer
)


class DocumentCategoryViewSet(viewsets.ModelViewSet):
    queryset = DocumentCategory.objects.select_related('parent').all()
    serializer_class = DocumentCategorySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name', 'code']
    filterset_fields = ['parent', 'requires_validation', 'is_active']


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.select_related(
        'category', 'site', 'academic_year', 'student__user',
        'uploaded_by', 'validated_by'
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'description', 'file_name', 'tags']
    ordering_fields = ['created_at', 'title', 'status']
    filterset_fields = ['category', 'site', 'academic_year', 'student', 'status', 'is_active']

    def get_serializer_class(self):
        if self.action == 'list':
            return DocumentListSerializer
        if self.action == 'create':
            return DocumentUploadSerializer
        return DocumentSerializer

    def perform_create(self, serializer):
        category = serializer.validated_data.get('category')
        initial_status = 'PENDING' if category.requires_validation else 'VALIDATED'
        serializer.save(uploaded_by=self.request.user, status=initial_status)

    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        document = self.get_object()
        notes = request.data.get('notes', '')
        document.validate(request.user, notes)
        return Response(DocumentSerializer(document).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        document = self.get_object()
        notes = request.data.get('notes', '')
        if not notes:
            return Response(
                {'detail': 'Le motif de rejet est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        document.reject(request.user, notes)
        return Response(DocumentSerializer(document).data)


class ArchiveViewSet(viewsets.ModelViewSet):
    queryset = Archive.objects.select_related(
        'site', 'academic_year', 'created_by'
    ).prefetch_related('archive_documents__document').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['archived_at', 'name']
    filterset_fields = ['site', 'academic_year', 'is_active']

    def get_serializer_class(self):
        if self.action == 'list':
            return ArchiveListSerializer
        return ArchiveSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='add-documents')
    def add_documents(self, request, pk=None):
        archive = self.get_object()
        document_ids = request.data.get('document_ids', [])
        
        added = 0
        for doc_id in document_ids:
            try:
                document = Document.objects.get(id=doc_id, status='VALIDATED')
                ArchiveDocument.objects.get_or_create(
                    archive=archive,
                    document=document,
                    defaults={'added_by': request.user}
                )
                added += 1
            except Document.DoesNotExist:
                continue
        
        return Response({
            'detail': f'{added} documents ajoutés à l\'archive',
            'archive': ArchiveSerializer(archive).data
        })

    @action(detail=True, methods=['post'], url_path='remove-document')
    def remove_document(self, request, pk=None):
        archive = self.get_object()
        document_id = request.data.get('document_id')
        
        try:
            archive_doc = ArchiveDocument.objects.get(
                archive=archive, document_id=document_id
            )
            document = archive_doc.document
            archive_doc.delete()
            document.status = 'VALIDATED'
            document.save()
            return Response({'detail': 'Document retiré de l\'archive'})
        except ArchiveDocument.DoesNotExist:
            return Response(
                {'detail': 'Document non trouvé dans l\'archive'},
                status=status.HTTP_404_NOT_FOUND
            )
