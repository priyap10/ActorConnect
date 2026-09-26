from django import forms

from apps.portfolio.models import MediaItem

from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("body", "media")
        widgets = {"body": forms.Textarea(attrs={"rows": 3, "placeholder": "Share an update, a scene or a call for actors"})}
        labels = {"body": "Your post", "media": "Attach from your portfolio"}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["media"].queryset = MediaItem.objects.filter(owner=user, is_public=True)
        self.fields["media"].required = False
        self.fields["media"].empty_label = "No attachment"

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if not body:
            raise forms.ValidationError("Write something before posting.")
        return body


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("body",)
        widgets = {"body": forms.Textarea(attrs={"rows": 2, "placeholder": "Add a comment"})}
        labels = {"body": "Comment"}

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if not body:
            raise forms.ValidationError("Write a comment first.")
        return body