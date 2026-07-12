from django.urls import path

from .views import (
    AnalysisListView,
    BalanceSheetListView,
    CashFlowListView,
    CompanyDetailView,
    CompanyListView,
    CompanySnapshotView,
    LegacyMetricsView,
    MLScoreListView,
    ProfitLossListView,
)

urlpatterns = [
    path("companies/", CompanyListView.as_view(), name="company-list"),
    path("companies/<str:symbol>/", CompanyDetailView.as_view(), name="company-detail"),
    path("financials/profit-loss/", ProfitLossListView.as_view(), name="profit-loss"),
    path("financials/balance-sheet/", BalanceSheetListView.as_view(), name="balance-sheet"),
    path("financials/cash-flow/", CashFlowListView.as_view(), name="cash-flow"),
    path("analysis/", AnalysisListView.as_view(), name="analysis"),
    path("ml-scores/", MLScoreListView.as_view(), name="ml-scores"),
    path("metrics/csv/", LegacyMetricsView.as_view(), name="metrics-csv"),
    path("snapshot/<str:symbol>/", CompanySnapshotView.as_view(), name="snapshot"),
]
