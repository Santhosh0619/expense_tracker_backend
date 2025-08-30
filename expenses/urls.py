from django.urls import path
from . import views

urlpatterns = [
    # Module 2: Dashboard
    path('dashboard/<int:year>/<int:month>/', views.dashboard, name='dashboard'),

    # Module 3: Expense Entry
    path('expenses/', views.expenses_crud, name='expenses_crud'),

    # Module 4: Budget Management
    path('budget/<int:year>/<int:month>/', views.budget_crud, name='budget_crud'),

    # Module 5: Category-wise Analysis
    path('analysis/<int:year>/<int:month>/', views.category_analysis, name='category_analysis'),

    # Module 6: History & Reports (+ Excel export)
    path('history/', views.history, name='history'),
    path('export/<int:year>/<int:month>/', views.export_excel, name='export_excel'),
]
