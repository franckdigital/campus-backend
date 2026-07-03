from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import (
    ZoomMeetingViewSet, CreateZoomMeetingView,
    LessonViewSet, LessonAttachmentViewSet, ChapterViewSet, LearningPathView,
    QuizViewSet, QuestionViewSet, ChoiceViewSet, QuizAttemptViewSet,
    AssignmentViewSet, AssignmentSubmissionViewSet,
    SubmitAssignmentView, CorrectSubmissionView,
    LibraryDocumentViewSet,
    SecureExamViewSet, ExamSessionSnapshotView,
    ExamSessionGradeView, ExamSessionSubmitFileView,
    VirtualLabViewSet, LabSubmissionViewSet,
    AIConversationViewSet, AIGenerateView, AIGradeView,
    VideoLibraryViewSet,
    VirtualClassroomViewSet, MeetingSegmentViewSet,
    CourseViewSet, CourseSectionViewSet, CourseChapterViewSet, CourseLessonViewSet,
)

router = DefaultRouter()
router.register(r'zoom-meetings', ZoomMeetingViewSet, basename='zoom-meeting')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'lesson-attachments', LessonAttachmentViewSet, basename='lesson-attachment')
router.register(r'chapters', ChapterViewSet, basename='chapter')
router.register(r'quizzes', QuizViewSet, basename='quiz')
router.register(r'quiz-questions', QuestionViewSet, basename='quiz-question')
router.register(r'quiz-choices', ChoiceViewSet, basename='quiz-choice')
router.register(r'quiz-attempts', QuizAttemptViewSet, basename='quiz-attempt')
router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'submissions', AssignmentSubmissionViewSet, basename='submission')
# Lot 14
router.register(r'library', LibraryDocumentViewSet, basename='library-document')
# Lot 12
router.register(r'exams', SecureExamViewSet, basename='secure-exam')
# Lot 13
router.register(r'labs', VirtualLabViewSet, basename='virtual-lab')
router.register(r'lab-submissions', LabSubmissionViewSet, basename='lab-submission')
# Lots 15/16/17
router.register(r'ai-conversations', AIConversationViewSet, basename='ai-conversation')
# Lot 9 — Vidéothèque
router.register(r'videos', VideoLibraryViewSet, basename='video')
# Lot 8 — Classes virtuelles
router.register(r'classrooms', VirtualClassroomViewSet, basename='classroom')
router.register(r'meeting-segments', MeetingSegmentViewSet, basename='meeting-segment')
# Cours autonomes
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'course-sections', CourseSectionViewSet, basename='course-section')
router.register(r'course-chapters', CourseChapterViewSet, basename='course-chapter')
router.register(r'course-lessons', CourseLessonViewSet, basename='course-lesson')

urlpatterns = [
    path('elearning/zoom/create-meeting/', CreateZoomMeetingView.as_view(), name='zoom-create-meeting'),
    path('elearning/assignments/<uuid:assignment_id>/submit/', SubmitAssignmentView.as_view(), name='submit-assignment'),
    path('elearning/submissions/<uuid:submission_id>/correct/', CorrectSubmissionView.as_view(), name='correct-submission'),
    path('elearning/learning-path/', LearningPathView.as_view(), name='learning-path'),
    path('elearning/ai/generate/', AIGenerateView.as_view(), name='ai-generate'),
    path('elearning/ai/grade/', AIGradeView.as_view(), name='ai-grade'),
    path('elearning/exams/sessions/<uuid:session_id>/snapshot/', ExamSessionSnapshotView.as_view(), name='exam-snapshot'),
    path('elearning/exam-sessions/<uuid:session_id>/grade/', ExamSessionGradeView.as_view(), name='exam-session-grade'),
    path('elearning/exam-sessions/<uuid:session_id>/submit-file/', ExamSessionSubmitFileView.as_view(), name='exam-session-submit-file'),
    path('elearning/', include(router.urls)),
]
