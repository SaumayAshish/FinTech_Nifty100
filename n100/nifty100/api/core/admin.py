from django.contrib import admin

from .models import Company

# ProfitLoss, BalanceSheet, and CashFlow use a composite primary key
# (symbol, year) to match their actual DB schema. Django admin does not
# support registering composite-primary-key models (as of Django 6.0), so
# they are intentionally not registered here.


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["symbol", "company_name", "sector", "sub_sector", "roce", "roe"]
    search_fields = ["symbol", "company_name", "sector", "sub_sector"]
