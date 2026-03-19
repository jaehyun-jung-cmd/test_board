from django.urls import path
from . import views

app_name = 'stocks'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/search/', views.api_search, name='api_search'),
    path('api/quote/', views.api_quote, name='api_quote'),
]
