from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls import url

urlpatterns = [
    path('', views.home, name='blog-home'),
    path('about/', views.about, name='blog-about'),
    url(r'^load_tickers/$', views.load_tickers, name='load_tickers'),
    url(r'^data_calculations/$', views.data_calculations, name='data_calculations'),
    url(r'^custom_screener/$', views.custom_screener, name='custom_screener'),
]
