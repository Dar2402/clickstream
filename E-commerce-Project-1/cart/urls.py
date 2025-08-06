from django.urls import path
from . import views
# from django.views.generic import TemplateView

app_name = 'cart'

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    # path('', TemplateView.as_view(template_name='base.html')),
]