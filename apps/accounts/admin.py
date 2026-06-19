from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, Permission, UserRole, UserSite


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'user_type', 'site', 'is_active', 'is_staff']
    list_filter = ['user_type', 'is_active', 'is_staff', 'site']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['last_name', 'first_name']
    readonly_fields = ['last_login', 'date_joined']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations personnelles', {'fields': ('first_name', 'last_name', 'phone', 'avatar')}),
        ('Type et site', {'fields': ('user_type', 'site')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'user_type', 'site'),
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_system', 'is_active', 'created_at']
    list_filter = ['is_system', 'is_active']
    search_fields = ['name', 'code']


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'module', 'is_active']
    list_filter = ['module', 'is_active']
    search_fields = ['code', 'name']


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'site', 'is_active', 'created_at']
    list_filter = ['role', 'site', 'is_active']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']


@admin.register(UserSite)
class UserSiteAdmin(admin.ModelAdmin):
    list_display = ['user', 'site', 'is_default', 'created_at']
    list_filter = ['site', 'is_default']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
