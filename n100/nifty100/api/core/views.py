from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics
from rest_framework.response import Response

from .models import Analysis, BalanceSheet, CashFlow, Company, MLScore, ProfitLoss
from .serializers import (
    AnalysisSerializer,
    BalanceSheetSerializer,
    CashFlowSerializer,
    CompanyDetailSerializer,
    CompanyListSerializer,
    MLScoreSerializer,
    ProfitLossSerializer,
    SnapshotSerializer,
)


class CompanyListView(generics.ListAPIView):
    queryset = Company.objects.all().order_by("symbol")
    serializer_class = CompanyListSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["symbol", "company_name", "sector", "sub_sector"]
    ordering_fields = ["symbol", "company_name", "sector", "roce", "roe", "book_value"]


class CompanyDetailView(generics.RetrieveAPIView):
    queryset = Company.objects.prefetch_related("documents", "pros_cons")
    serializer_class = CompanyDetailSerializer
    lookup_field = "symbol"


class ProfitLossListView(generics.ListAPIView):
    serializer_class = ProfitLossSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["symbol", "year"]
    ordering_fields = ["year__sort_order", "sales", "net_profit", "eps", "net_profit_margin_pct"]
    ordering = ["symbol", "year__sort_order"]

    def get_queryset(self):
        return ProfitLoss.objects.select_related("symbol", "year")


class BalanceSheetListView(generics.ListAPIView):
    serializer_class = BalanceSheetSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["symbol", "year"]
    ordering_fields = ["year__sort_order", "total_assets", "borrowings", "debt_to_equity"]
    ordering = ["symbol", "year__sort_order"]

    def get_queryset(self):
        return BalanceSheet.objects.select_related("symbol", "year")


class CashFlowListView(generics.ListAPIView):
    serializer_class = CashFlowSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["symbol", "year"]
    ordering_fields = ["year__sort_order", "operating_activity", "free_cash_flow", "cash_conversion_ratio"]
    ordering = ["symbol", "year__sort_order"]

    def get_queryset(self):
        return CashFlow.objects.select_related("symbol", "year")


class AnalysisListView(generics.ListAPIView):
    serializer_class = AnalysisSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["symbol", "period_label"]
    ordering_fields = ["period_label", "compounded_sales_growth_pct", "compounded_profit_growth_pct"]
    ordering = ["symbol", "period_label"]

    def get_queryset(self):
        return Analysis.objects.select_related("symbol")


class MLScoreListView(generics.ListAPIView):
    serializer_class = MLScoreSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["symbol", "health_label"]
    ordering_fields = ["computed_at", "overall_score", "profitability_score", "growth_score"]
    ordering = ["-computed_at"]

    def get_queryset(self):
        return MLScore.objects.select_related("symbol", "health_label")


class LegacyMetricsView(ProfitLossListView):
    """
    Kept at the legacy /api/metrics/csv/ URL for backward compatibility.

    Originally read data/clean/fact_profit_loss.csv directly at request
    time, a separate data path from every other endpoint here. Now backed
    by the same Postgres-backed queryset as /api/financials/profit-loss/
    so the two can no longer drift apart.
    """


def _latest_by_year(queryset):
    return queryset.order_by("-year__sort_order").first()


class CompanySnapshotView(generics.GenericAPIView):
    serializer_class = SnapshotSerializer

    def get(self, request, symbol):
        company = get_object_or_404(
            Company.objects.prefetch_related("documents", "pros_cons"),
            symbol=symbol.upper(),
        )
        data = {
            "company": company,
            "latest_profit_loss": _latest_by_year(
                ProfitLoss.objects.select_related("symbol", "year").filter(symbol=company)
            ),
            "latest_balance_sheet": _latest_by_year(
                BalanceSheet.objects.select_related("symbol", "year").filter(symbol=company)
            ),
            "latest_cash_flow": _latest_by_year(
                CashFlow.objects.select_related("symbol", "year").filter(symbol=company)
            ),
            "analysis": Analysis.objects.select_related("symbol").filter(symbol=company),
            "latest_ml_score": MLScore.objects.select_related("symbol", "health_label")
            .filter(symbol=company)
            .order_by("-computed_at")
            .first(),
        }
        return Response(self.get_serializer(data).data)
