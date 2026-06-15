from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AlertaViewSet, ConfiguracionAlertaViewSet

router = DefaultRouter()
router.register(r'alertas', AlertaViewSet, basename='alerta')
router.register(r'configuracion', ConfiguracionAlertaViewSet, basename='configuracion')

urlpatterns = [
    path('', include(router.urls)),
]
