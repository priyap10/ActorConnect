from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.mixins import safe_next
from apps.core.permissions import verified_required
from apps.network.models import Connection

from .forms import CommentForm, PostForm
from .models import Comment, Like, Post

POSTS_PER_PAGE = 10


def _posts_queryset():
    return (
        Post.objects.select_related("author", "author__actor_profile", "author__casting_profile", "media")
        .annotate(like_count=Count("likes", distinct=True), comment_count=Count("comments", distinct=True))
        .order_by("-created_at")
    )


def _mark_liked(posts, user):
    liked = set(Like.objects.filter(user=user, post__in=posts).values_list("post_id", flat=True))
    for post in posts:
        post.liked = post.pk in liked


@verified_required
def home(request):
    scope = "all" if request.GET.get("scope") == "all" else "network"
    posts = _posts_queryset()
    if scope == "network":
        ids = Connection.objects.connected_ids(request.user)
        posts = posts.filter(Q(author=request.user) | Q(author_id__in=ids))
    page = Paginator(posts, POSTS_PER_PAGE).get_page(request.GET.get("page"))
    _mark_liked(page.object_list, request.user)
    return render(
        request,
        "feed/home.html",
        {"page_obj": page, "scope": scope, "form": PostForm(user=request.user)},
    )


@require_POST
@verified_required
def post_create(request):
    form = PostForm(request.POST, user=request.user)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        messages.success(request, "Your post is live.")
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    return redirect("feed:home")


@verified_required
def post_detail(request, pk):
    post = get_object_or_404(_posts_queryset(), pk=pk)
    _mark_liked([post], request.user)
    comments = post.comments.select_related("author", "author__actor_profile", "author__casting_profile")
    return render(
        request,
        "feed/post_detail.html",
        {"post": post, "comments": comments, "form": CommentForm()},
    )


@require_POST
@verified_required
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    post.delete()
    messages.success(request, "Post deleted.")
    return redirect("feed:home")


@require_POST
@verified_required
def like_toggle(request, pk):
    post = get_object_or_404(Post, pk=pk)
    like, created = Like.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()
    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"liked": created, "count": post.likes.count()})
    return redirect(safe_next(request, post.get_absolute_url()))


@require_POST
@verified_required
def comment_create(request, pk):
    post = get_object_or_404(Post, pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post, comment.author = post, request.user
        comment.save()
    else:
        for error in form.errors.get("body", []):
            messages.error(request, error)
    return redirect(post)


@require_POST
@verified_required
def comment_delete(request, pk):
    comment = get_object_or_404(
        Comment.objects.filter(Q(author=request.user) | Q(post__author=request.user)), pk=pk
    )
    post = comment.post
    comment.delete()
    messages.success(request, "Comment deleted.")
    return redirect(post)