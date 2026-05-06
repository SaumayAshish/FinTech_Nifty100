from django.contrib import admin

from .models import BalanceSheet, CashFlow, Company, ProfitLoss


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["symbol", "company_name", "sector", "sub_sector", "roce", "roe"]
    search_fields = ["symbol", "company_name", "sector", "sub_sector"]


@admin.register(ProfitLoss)
class ProfitLossAdmin(admin.ModelAdmin):
    list_display = ["symbol", "year", "sales", "net_profit", "eps"]
    search_fields = ["symbol__symbol", "symbol__company_name"]


@admin.register(BalanceSheet)
class BalanceSheetAdmin(admin.ModelAdmin):
    list_display = ["symbol", "year", "total_assets", "borrowings", "debt_to_equity"]
    search_fields = ["symbol__symbol", "symbol__company_name"]


@admin.register(CashFlow)
class CashFlowAdmin(admin.ModelAdmin):
    list_display = ["symbol", "year", "operating_activity", "free_cash_flow", "cash_conversion_ratio"]
    search_fields = ["symbol__symbol", "symbol__company_name"]
