# myapp/urls.py
from django.urls import path
from .views import custom_login, home,QR_login
from .views import qr_code_decoder, video_feed

urlpatterns = [
    path('qr_code_decoder/', qr_code_decoder, name='qr_code_decoder'),
    path('video_feed/', video_feed, name='video_feed'),
    path('custom_login/', custom_login, name='custom_login'),
    path('home/', home, name='home'),
    path('QR_login/', QR_login, name='QR_login'),
]
