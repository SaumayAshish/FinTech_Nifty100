from django.urls import path
from .views import (
    CompanyListView,
    CompanyDetailView,
    ProfitLossListView,
    BalanceSheetListView,
    CashFlowListView,
    MetricsListView,
    MetricsFromCSVView,
    CompanySnapshotView,
    TopCompaniesView,
)

urlpatterns = [
    # Companies
    path("companies/",                   CompanyListView.as_view(),     name="company-list"),
    path("companies/<str:company_id>/",  CompanyDetailView.as_view(),   name="company-detail"),

    # Financials (DB-backed)
    path("financials/profit-loss/",      ProfitLossListView.as_view(),  name="profit-loss"),
    path("financials/balance-sheet/",    BalanceSheetListView.as_view(),name="balance-sheet"),
    path("financials/cash-flow/",        CashFlowListView.as_view(),    name="cash-flow"),

    # Metrics (DB-backed)
    path("metrics/",                     MetricsListView.as_view(),     name="metrics"),

    # CSV-backed endpoints (no DB needed)
    path("metrics/csv/",                 MetricsFromCSVView.as_view(),  name="metrics-csv"),
    path("snapshot/<str:company_id>/",   CompanySnapshotView.as_view(), name="snapshot"),
    path("top/",                         TopCompaniesView.as_view(),    name="top-companies"),
]
