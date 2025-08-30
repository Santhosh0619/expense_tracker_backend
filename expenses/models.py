from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    # Examples: Food, Restaurant, Entertainment, Travel, Bills, Groceries, Other
    name = models.CharField(max_length=50, unique=True)
    # optional grouping if you want “Food” vs “Restaurant” inside “Food & Dining”
    group = models.CharField(max_length=50, blank=True, default='')

    def __str__(self):
        return self.name

class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    year = models.IntegerField()
    month = models.IntegerField()  # 1..12
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2)
    monthly_budget = models.DecimalField(max_digits=12, decimal_places=2)  # can = salary or custom

    class Meta:
        unique_together = ('user','year','month')

    def __str__(self):
        return f'{self.user.username} {self.month}/{self.year}'

class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.CharField(max_length=255, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} {self.category.name} ₹{self.amount} on {self.date}'
