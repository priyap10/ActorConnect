from django.contrib import admin

from .models import Comment, Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("author", "short_body", "created_at")
    search_fields = ("body", "author__email", "author__full_name")
    raw_id_fields = ("author", "media")

    @admin.display(description="Post")
    def short_body(self, obj):
        return obj.body[:80]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "post", "created_at")
    search_fields = ("body", "author__email")
    raw_id_fields = ("author", "post")