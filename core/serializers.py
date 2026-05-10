from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Workspace, WorkspaceMember, Tag, Document, DocumentVersion, Comment, AuditLog

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    token = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'password', 'token']

    def get_token(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user

class WorkspaceSerializer(serializers.ModelSerializer):
    members_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Workspace
        fields = ['id', 'name', 'description', 'created_at', 'is_active', 'members_count']

class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)

    class Meta:
        model = WorkspaceMember
        fields = ['id', 'workspace', 'user', 'user_details', 'role', 'joined_at']
        read_only_fields = ['workspace']

    def validate_role(self, value):
        if value not in [choice[0] for choice in WorkspaceMember.Role.choices]:
            raise serializers.ValidationError("Invalid role provided.")
        return value

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color_code']

class DocumentSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    current_version_number = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ['id', 'title', 'content', 'workspace', 'created_by', 'created_at', 'updated_at', 'status', 'tags', 'current_version_number']
        read_only_fields = ['created_by', 'workspace']

    def get_current_version_number(self, obj):
        return obj.versions.count()

class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = ['id', 'document', 'content', 'version_number', 'created_at', 'created_by']

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'document', 'user', 'content', 'parent', 'created_at']
        read_only_fields = ['user', 'document']

    def validate(self, data):
        parent = data.get('parent')
        document = self.context.get('document')
        
        if parent and parent.document != document:
            raise serializers.ValidationError({"parent": "Parent comment must belong to the same document."})
        return data

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ['id', 'model_name', 'object_id', 'action', 'actor', 'timestamp']
