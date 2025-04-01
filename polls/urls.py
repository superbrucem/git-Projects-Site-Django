from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("process/", views.process_youtube, name="process_youtube"),
    path("download/", views.download_file, name="download_file"),
]
