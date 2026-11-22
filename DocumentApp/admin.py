from django.contrib import admin
from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('idDocument', 'titreDocument', 'created_at', 'updated_at')
    list_display_links = ('idDocument', 'titreDocument')
    search_fields = ('titreDocument', 'descDocument')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
