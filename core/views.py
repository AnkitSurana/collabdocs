from django.shortcuts import get_object_or_404
from django.db import transaction, IntegrityError
from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import User, Workspace, WorkspaceMember, Tag, Document, DocumentVersion, Comment, AuditLog
from .serializers import (
    UserSerializer, RegisterSerializer, WorkspaceSerializer, 
    WorkspaceMemberSerializer, TagSerializer, DocumentSerializer, 
    DocumentVersionSerializer, CommentSerializer, AuditLogSerializer
)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == 'register':
            return [AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def profile(self, request):
        user = request.user
        serializer = self.get_serializer(user)
        workspaces_count = WorkspaceMember.objects.filter(user=user).aggregate(count=Count('id'))['count']
        data = serializer.data
        data['workspaces_count'] = workspaces_count
        return Response(data)

    @action(detail=True, methods=['get'])
    def workspaces(self, request, pk=None):
        user = self.get_object()
        memberships = WorkspaceMember.objects.filter(user=user).select_related('workspace')
        workspaces = [m.workspace for m in memberships]
        serializer = WorkspaceSerializer(workspaces, many=True)
        return Response(serializer.data)

class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Workspace.objects.annotate(members_count=Count('members', distinct=True))

    @transaction.atomic
    def perform_create(self, serializer):
        workspace = serializer.save()
        WorkspaceMember.objects.create(workspace=workspace, user=self.request.user, role=WorkspaceMember.Role.ADMIN)
        
        if self.request.data.get('simulate_failure'):
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"error": "Simulated failure! The transaction rolled back, so the workspace was NOT saved."})

    @action(detail=True, methods=['post'])
    def members(self, request, pk=None):
        workspace = self.get_object()
        user_id = request.data.get('user')
        role = request.data.get('role', WorkspaceMember.Role.VIEWER)
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User does not exist."}, status=status.HTTP_404_NOT_FOUND)
            
        try:
            member = WorkspaceMember.objects.create(workspace=workspace, user=user, role=role)
            serializer = WorkspaceMemberSerializer(member)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response({"error": "User is already a member of this workspace."}, status=status.HTTP_409_CONFLICT)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        workspace = self.get_object()
        stats = Workspace.objects.filter(id=workspace.id).aggregate(
            total_documents=Count('documents', distinct=True),
            total_members=Count('members', distinct=True)
        )
        return Response(stats)

    @action(detail=True, methods=['get', 'post'])
    def documents(self, request, pk=None):
        workspace = self.get_object()
        if request.method == 'POST':
            serializer = DocumentSerializer(data=request.data)
            if serializer.is_valid():
                with transaction.atomic():
                    doc = serializer.save(workspace=workspace, created_by=request.user)
                    DocumentVersion.objects.create(
                        document=doc,
                        content=doc.content,
                        version_number=1,
                        created_by=request.user
                    )
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            queryset = Document.objects.filter(workspace=workspace).select_related('created_by')
            
            status_param = request.query_params.get('status')
            if status_param:
                queryset = queryset.filter(status=status_param)
                
            search_param = request.query_params.get('search')
            if search_param:
                queryset = queryset.filter(Q(title__icontains=search_param) | Q(content__icontains=search_param))
                
            tags_param = request.query_params.get('tags')
            if tags_param:
                tag_ids = tags_param.split(',')
                queryset = queryset.filter(tags__id__in=tag_ids)
                
            date_gte = request.query_params.get('created_gte')
            if date_gte:
                queryset = queryset.filter(created_at__gte=date_gte)
                
            serializer = DocumentSerializer(queryset, many=True)
            return Response(serializer.data)

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all().select_related('workspace', 'created_by').prefetch_related('tags')
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def perform_update(self, serializer):
        doc = serializer.save()
        version_number = doc.versions.count() + 1
        DocumentVersion.objects.create(
            document=doc,
            content=doc.content,
            version_number=version_number,
            created_by=self.request.user
        )

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        document = self.get_object()
        versions = document.versions.all().select_related('created_by')
        serializer = DocumentVersionSerializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'get'])
    def comments(self, request, pk=None):
        document = self.get_object()
        if request.method == 'POST':
            serializer = CommentSerializer(data=request.data, context={'document': document})
            if serializer.is_valid():
                serializer.save(user=request.user, document=document)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            comments = document.comments.all().select_related('user', 'parent')
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def tags(self, request, pk=None):
        document = self.get_object()
        tag_ids = request.data.get('tag_ids', [])
        tags = Tag.objects.filter(id__in=tag_ids)
        document.tags.add(*tags)
        
        current_tags = document.tags.values_list('id', flat=True)
        return Response({"status": "Tags added", "current_tags": list(current_tags)})

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        document = self.get_object()
        stats = Document.objects.filter(id=document.id).aggregate(
            total_comments=Count('comments', distinct=True),
            total_versions=Count('versions', distinct=True)
        )
        return Response(stats)

class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all().select_related('actor')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        model_name = self.request.query_params.get('model_name')
        if model_name:
            queryset = queryset.filter(model_name__icontains=model_name)
        action_param = self.request.query_params.get('action')
        if action_param:
            queryset = queryset.filter(action=action_param)
        return queryset
