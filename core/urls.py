from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Module 1: Auth
    path('api/auth/', include('accounts.urls')),

    # Modules 2–6: Expenses, Budgets, Reports, Dashboard
    path('api/', include('expenses.urls')),
]
