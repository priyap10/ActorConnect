from django.contrib import admin

from .models import Conversation


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("user_a", "user_b", "updated_at")
    raw_id_fields = ("user_a", "user_b")