from django.views.generic import ListView, DetailView
from django.db.models import Q, Count, F
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Category, Tag, Post


class PostListView(ListView):
    """لیست مقالات منتشر شده"""
    model = Post
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = 9

    def get_queryset(self):
        qs = (
            Post.objects
            .filter(status=Post.Status.PUBLISHED)
            .select_related("category", "author")
            .prefetch_related("tags")
        )

        # فیلتر دسته‌بندی از URL
        category_slug = self.kwargs.get("category_slug")
        if category_slug:
            self.category = get_object_or_404(
                Category, slug=category_slug, is_active=True
            )
            qs = qs.filter(category=self.category)
        else:
            self.category = None

        # فیلتر برچسب از URL
        tag_slug = self.kwargs.get("tag_slug")
        if tag_slug:
            self.tag = get_object_or_404(Tag, slug=tag_slug)
            qs = qs.filter(tags=self.tag)
        else:
            self.tag = None

        # جستجو
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(excerpt__icontains=q)
                | Q(content__icontains=q)
            )

        # فقط ویژه
        if self.request.GET.get("featured") == "1":
            qs = qs.filter(is_featured=True)

        # مرتب‌سازی
        sort = self.request.GET.get("sort", "newest")
        if sort == "oldest":
            qs = qs.order_by("published_at")
        elif sort == "views":
            qs = qs.order_by("-views_count")
        elif sort == "title":
            qs = qs.order_by("title")
        else:
            qs = qs.order_by("-published_at", "-created_at")

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = (
            Category.objects
            .filter(is_active=True)
            .annotate(
                post_count=Count(
                    "posts",
                    filter=Q(posts__status=Post.Status.PUBLISHED),
                )
            )
            .order_by("order", "name")
        )
        context["tags"] = (
            Tag.objects
            .annotate(
                post_count=Count(
                    "posts",
                    filter=Q(posts__status=Post.Status.PUBLISHED),
                )
            )
            .filter(post_count__gt=0)
            .order_by("name")
        )
        context["current_category"] = getattr(self, "category", None)
        context["current_tag"] = getattr(self, "tag", None)
        context["search_query"] = self.request.GET.get("q", "")
        return context


class PostDetailView(DetailView):
    """صفحه جزئیات یک مقاله"""
    model = Post
    template_name = "blog/post_detail.html"
    context_object_name = "post"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            Post.objects
            .filter(status=Post.Status.PUBLISHED)
            .select_related("category", "author")
            .prefetch_related("tags")
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # افزایش تعداد بازدید
        Post.objects.filter(pk=obj.pk).update(views_count=F("views_count") + 1)
        obj.views_count += 1
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object

        # مقالات مرتبط (همان دسته، غیر از خودش)
        related = (
            Post.objects
            .filter(
                category=post.category,
                status=Post.Status.PUBLISHED,
            )
            .exclude(pk=post.pk)
            .select_related("category", "author")[:3]
        )
        context["related_posts"] = related
        context["categories"] = (
            Category.objects.filter(is_active=True).order_by("order", "name")
        )
        return context
from django.shortcuts import render

# Create your views here.
