from pathlib import Path

import pandas as pd
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Analysis, BalanceSheet, CashFlow, Company, MLScore, ProfitLoss
from .serializers import (
    AnalysisSerializer,
    BalanceSheetSerializer,
    CashFlowSerializer,
    CompanyDetailSerializer,
    CompanyListSerializer,
    MLScoreSerializer,
    ProfitLossSerializer,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "clean"


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


class MetricsFromCSVView(APIView):
    def get(self, request):
        path = DATA_DIR / "fact_profit_loss.csv"
        if not path.exists():
            return Response({"error": "fact_profit_loss.csv not found. Run ETL first."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        df = pd.read_csv(path)
        symbol = request.query_params.get("symbol")
        year_label = request.query_params.get("year_label")
        sort_by = request.query_params.get("sort", "year_id")
        desc = request.query_params.get("desc", "true").lower() == "true"
        limit = int(request.query_params.get("limit", 100))

        if symbol:
            df = df[df["symbol"].str.upper() == symbol.upper()]
        if year_label and "year_label" in df.columns:
            df = df[df["year_label"].astype(str) == year_label]
        if sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=not desc, na_position="last")

        df = df.head(limit)
        return Response({"count": len(df), "results": df.where(pd.notna(df), None).to_dict(orient="records")})


class CompanySnapshotView(APIView):
    def get(self, request, symbol):
        symbol = symbol.upper()
        companies_path = DATA_DIR / "dim_company.csv"
        if not companies_path.exists():
            return Response({"error": "Clean warehouse CSVs not found. Run ETL first."}, status=503)

        company_df = pd.read_csv(companies_path)
        pl_path = DATA_DIR / "fact_profit_loss.csv"
        bs_path = DATA_DIR / "fact_balance_sheet.csv"
        cf_path = DATA_DIR / "fact_cash_flow.csv"
        analysis_path = DATA_DIR / "fact_analysis.csv"

        company_rows = company_df[company_df["symbol"].str.upper() == symbol]
        if company_rows.empty:
            return Response({"error": f"Company '{symbol}' not found."}, status=404)

        payload = {"company": company_rows.iloc[0].where(pd.notna(company_rows.iloc[0]), None).to_dict()}

        def latest_record(path):
            if not path.exists():
                return None
            df = pd.read_csv(path)
            df = df[df["symbol"].str.upper() == symbol]
            if df.empty:
                return None
            sort_col = "sort_order" if "sort_order" in df.columns else "year_id"
            row = df.sort_values(sort_col).iloc[-1]
            return row.where(pd.notna(row), None).to_dict()

        payload["latest_profit_loss"] = latest_record(pl_path)
        payload["latest_balance_sheet"] = latest_record(bs_path)
        payload["latest_cash_flow"] = latest_record(cf_path)

        if analysis_path.exists():
            df = pd.read_csv(analysis_path)
            df = df[df["symbol"].str.upper() == symbol]
            payload["analysis"] = df.where(pd.notna(df), None).to_dict(orient="records")
        else:
            payload["analysis"] = []

        return Response(payload)
