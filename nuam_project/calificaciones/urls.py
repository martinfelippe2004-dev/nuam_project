from django.urls import path
from . import views

urlpatterns = [
    path('', views.mantenedor_calificaciones, name='mantenedor'),
    path('guardar/', views.guardar_calificacion, name='guardar_calificacion'),
    path('eliminar/<int:calificacion_id>/', views.eliminar_calificacion, name='eliminar_calificacion'),
    path('carga-masiva/', views.carga_masiva_csv, name='carga_masiva_csv'),
]