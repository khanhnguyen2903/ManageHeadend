from django.urls import path
from .views import add_user, list_user, edit_user, delete_user, login_user, logout_user, change_password

urlpatterns = [
    path('add-user/', add_user, name='add_user'),
    path('list-user/', list_user, name='list_user'),
    path('edit-user/<str:phone>/', edit_user, name='edit_user'),
    path('delete-user/<str:phone>/', delete_user, name='delete_user'),
    path('', login_user, name='login_user'),
    path('logout/', logout_user, name='logout_user'),
    path('change-password/', change_password, name='change_password'),
]
