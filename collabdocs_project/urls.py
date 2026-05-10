from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from core.views import (
    UserViewSet, WorkspaceViewSet, DocumentViewSet, 
    TagViewSet, AuditLogViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'workspaces', WorkspaceViewSet, basename='workspace')
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'audit-logs', AuditLogViewSet, basename='auditlog')

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include(router.urls)),
]
