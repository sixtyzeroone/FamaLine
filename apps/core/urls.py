from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('artikel/', views.artikel_list, name='artikel_list'),
    path('artikel/<slug:slug>/', views.artikel_detail, name='artikel_detail'),
    path('taaruf/', views.taaruf, name='taaruf'),
    path('kelas/', views.kelas, name='kelas'),
    path('kelas/<int:kelas_id>/', views.kelas_detail, name='kelas_detail'),  # ← TAMBAHKAN INI
    path('checkout/<int:kelas_id>/', views.checkout, name='checkout'),
    path('payment/success/<str:order_id>/', views.payment_success, name='payment_success'),
    path('payment/failed/<str:order_id>/', views.payment_failed, name='payment_failed'),
    path('api/midtrans/notification/', views.midtrans_notification, name='midtrans_notification'),
    path('my-classes/', views.my_classes, name='my_classes'),
    path('konsultasi/', views.konsultasi, name='konsultasi'),
    path('subscribe/', views.subscribe_newsletter, name='subscribe'),
]
