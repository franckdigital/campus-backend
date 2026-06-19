from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import (
    ZoomMeetingViewSet, CreateZoomMeetingView,
    LessonViewSet, LessonAttachmentViewSet,
    AssignmentViewSet, AssignmentSubmissionViewSet,
    SubmitAssignmentView, CorrectSubmissionView
)

router = DefaultRouter()
router.register(r'zoom-meetings', ZoomMeetingViewSet, basename='zoom-meeting')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'lesson-attachments', LessonAttachmentViewSet, basename='lesson-attachment')
router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'submissions', AssignmentSubmissionViewSet, basename='submission')

urlpatterns = [
    path('elearning/zoom/create-meeting/', CreateZoomMeetingView.as_view(), name='zoom-create-meeting'),
    path('elearning/assignments/<uuid:assignment_id>/submit/', SubmitAssignmentView.as_view(), name='submit-assignment'),
    path('elearning/submissions/<uuid:submission_id>/correct/', CorrectSubmissionView.as_view(), name='correct-submission'),
    path('elearning/', include(router.urls)),
]
