from django.urls import path
from .views import PostListView, PostDetailView

app_name = "blog"

urlpatterns = [
    path("", PostListView.as_view(), name="post_list"),
    path("category/<slug:category_slug>/", PostListView.as_view(), name="post_list_by_category"),
    path("tag/<slug:tag_slug>/", PostListView.as_view(), name="post_list_by_tag"),
    path("<slug:slug>/", PostDetailView.as_view(), name="post_detail"),
]
