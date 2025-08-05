from django.contrib import admin
from django.urls import path
from myapp.views import todo_list, delete_todo

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', todo_list, name='todo_list'),
    path('delete/<int:todo_id>/', delete_todo, name='delete_todo'),
]