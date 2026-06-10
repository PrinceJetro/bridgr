from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    CustomUser,
    Institution,
    ExchangeVendor,
    VendorRate,
    Transaction,
    Notification,
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'country', 'is_vendor', 'is_email_verified', 'is_staff')
    list_filter = ('country', 'is_vendor', 'is_email_verified', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'phone_number')
    ordering = ('-created_at',)

    fieldsets = UserAdmin.fieldsets + (
        ('Bridgr profile', {
            'fields': ('country', 'phone_number', 'is_email_verified', 'is_vendor', 'avatar'),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Bridgr profile', {
            'fields': ('country', 'phone_number', 'is_vendor'),
        }),
    )


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'country', 'account_name', 'bank_name', 'is_verified', 'created_at')
    list_filter = ('category', 'country', 'is_verified')
    search_fields = ('name', 'account_name', 'bank_name', 'account_number')


class VendorRateInline(admin.TabularInline):
    model = VendorRate
    extra = 0


@admin.register(ExchangeVendor)
class ExchangeVendorAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user', 'location', 'is_verified', 'created_at')
    list_filter = ('is_verified',)
    search_fields = ('business_name', 'user__username', 'location')
    inlines = [VendorRateInline]


@admin.register(VendorRate)
class VendorRateAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'currency_pair', 'rate', 'updated_at')
    list_filter = ('currency_pair',)
    search_fields = ('vendor__business_name',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'sender', 'recipient_type', 'send_amount', 'send_currency',
        'receive_amount', 'receive_currency', 'status', 'created_at',
    )
    list_filter = ('status', 'recipient_type', 'send_currency', 'receive_currency', 'fee_type')
    search_fields = ('reference', 'recipient_name', 'recipient_email', 'sender__username')
    readonly_fields = ('reference', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'transaction', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('user__username', 'message')
    date_hierarchy = 'created_at'
