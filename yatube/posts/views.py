from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PostForm, CommentForm
from .models import Group, Post, User, Follow
from .post_settings import PAGINATOR_SET


def pagination(request, to_pagination):
    """Вспомогательная функция для паджинации."""
    paginator = Paginator(to_pagination, PAGINATOR_SET)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


def index(request):
    """View функция для главной страницы."""
    posts = Post.objects.all()
    page_obj = pagination(request, posts)
    context = {
        'page_obj': page_obj,
        'index': True,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    """View функция для страницы сообщества."""
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    page_obj = pagination(request, posts)
    template = 'posts/group_list.html'
    context = {
        'group': group,
        'posts': posts,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    """View функция для страницы профиля."""
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    count = posts.count()
    page_obj = pagination(request, posts)
    following = False
    if request.user.is_authenticated:
        following = Follow.objects.filter(
            user=request.user
        ).filter(
            author=author
        ).exists()
    context = {
        'page_obj': page_obj,
        'count': count,
        'author': author,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    """View функция для страницы поста."""
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.all()
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    author = post.author
    count = author.posts.all().count()
    context = {
        'count': count,
        'author': author,
        'post': post,
        'comments': comments,
        'form': form,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    """View функция для создания нового поста."""
    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect(
            'posts:profile', request.user.username)
    return render(request, 'posts/create_post.html', {'form': form})


def post_edit(request, post_id):
    """View функция для редактирования поста."""
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id)
    return render(
        request, 'posts/create_post.html',
        {'form': form, 'post': post}
    )


@login_required
def add_comment(request, post_id):
    """View функция для добавления комментария."""
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    user = get_object_or_404(User, username=request.user.username)
    follows = Follow.objects.filter(user=user).values_list('author_id')
    posts = Post.objects.filter(author_id__in=follows)
    page_obj = pagination(request, posts)
    context = {'page_obj': page_obj, 'follow': True}
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    if request.user.username == username:
        return redirect('posts:profile', username=username)
    author = get_object_or_404(User, username=username)
    already_follow = Follow.objects.filter(
        user=request.user,
        author=author
    ).exists()
    if already_follow:
        return redirect('posts:profile', username=username)
    follow = Follow(user=request.user, author=author)
    follow.save()
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    follow = get_object_or_404(
        Follow,
        user=request.user,
        author=author
    )
    follow.delete()
    return redirect('posts:profile', username=username)
