"""
API Views — NIFTY 100 Financial Analytics
==========================================
All endpoints support:
  ?search=<name>          full-text search on company name
  ?ordering=<field>       sort by any field (prefix - for descending)
  ?page=<n>               pagination (50 per page default)

Company-specific filters:
  /api/financials/profit-loss/?company_id=HDFCBANK
  /api/financials/profit-loss/?date_key=2024-03
"""

import os
from pathlib import Path

import pandas as pd
from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BalanceSheet, CashFlow, Company, FinancialMetrics, ProfitLoss
from .serializers import (
    BalanceSheetSerializer,
    CashFlowSerializer,
    CompanyDetailSerializer,
    CompanyListSerializer,
    CompanySnapshotSerializer,
    FinancialMetricsSerializer,
    ProfitLossSerializer,
)

# Path to pre-computed metrics CSV (used when DB is unavailable)
METRICS_CSV = Path(__file__).resolve().parent.parent.parent / "data/clean/metrics.csv"


# ---------------------------------------------------------------------------
# Company endpoints
# ---------------------------------------------------------------------------

class CompanyListView(generics.ListAPIView):
    """
    GET /api/companies/
    List all NIFTY 100 companies with key ratios.
    Supports ?search=name and ?ordering=roce_pct
    """
    queryset         = Company.objects.all().order_by("company_id")
    serializer_class = CompanyListSerializer
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ["company_name", "company_id"]
    ordering_fields  = ["company_name", "roce_pct", "roe_pct", "book_value"]


class CompanyDetailView(generics.RetrieveAPIView):
    """
    GET /api/companies/<company_id>/
    Full company profile including pros/cons and annual report links.
    """
    queryset         = Company.objects.prefetch_related("pros_cons", "documents")
    serializer_class = CompanyDetailSerializer
    lookup_field     = "company_id"


# ---------------------------------------------------------------------------
# Financials endpoints
# ---------------------------------------------------------------------------

class ProfitLossListView(generics.ListAPIView):
    """
    GET /api/financials/profit-loss/
    Filter: ?company_id=ABB  ?date_key=2024-03
    """
    serializer_class = ProfitLossSerializer
    filter_backends  = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["company_id", "date_key"]
    ordering_fields  = ["date_key", "sales", "net_profit", "eps"]
    ordering         = ["-date_key"]

    def get_queryset(self):
        return ProfitLoss.objects.select_related("company").all()


class BalanceSheetListView(generics.ListAPIView):
    """GET /api/financials/balance-sheet/"""
    serializer_class = BalanceSheetSerializer
    filter_backends  = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["company_id", "date_key"]
    ordering_fields  = ["date_key", "total_assets", "borrowings", "net_worth"]
    ordering         = ["-date_key"]

    def get_queryset(self):
        return BalanceSheet.objects.select_related("company").all()


class CashFlowListView(generics.ListAPIView):
    """GET /api/financials/cash-flow/"""
    serializer_class = CashFlowSerializer
    filter_backends  = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["company_id", "date_key"]
    ordering_fields  = ["date_key", "operating_activity", "free_cash_flow"]
    ordering         = ["-date_key"]

    def get_queryset(self):
        return CashFlow.objects.select_related("company").all()


# ---------------------------------------------------------------------------
# Metrics endpoints
# ---------------------------------------------------------------------------

class MetricsListView(generics.ListAPIView):
    """
    GET /api/metrics/
    All computed KPIs.  Filter: ?company_id=TCS  ?ordering=-roce_pct
    """
    serializer_class = FinancialMetricsSerializer
    filter_backends  = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["company_id", "date_key"]
    ordering_fields  = [
        "date_key", "net_profit_margin", "roce_pct", "roe_pct",
        "debt_to_equity", "free_cash_flow", "eps",
    ]
    ordering = ["-date_key"]

    def get_queryset(self):
        return FinancialMetrics.objects.select_related("company").all()


class MetricsFromCSVView(APIView):
    """
    GET /api/metrics/csv/
    Serves metrics directly from the pre-computed CSV (no DB required).
    Supports: ?company_id=  ?year=  ?sort=net_profit_margin_pct  ?limit=20
    """

    def get(self, request):
        if not METRICS_CSV.exists():
            return Response(
                {"error": "metrics.csv not found. Run: python etl/04_compute_metrics.py"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        df = pd.read_csv(METRICS_CSV)

        # Filter
        company_id = request.query_params.get("company_id")
        year       = request.query_params.get("year")
        if company_id:
            df = df[df["company_id"].str.upper() == company_id.upper()]
        if year:
            df = df[df["year"].astype(str).str.startswith(year)]

        # Sort
        sort_by = request.query_params.get("sort", "year")
        desc    = request.query_params.get("desc", "true").lower() == "true"
        if sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=not desc, na_position="last")

        # Limit
        limit = int(request.query_params.get("limit", 200))
        df    = df.head(limit)

        return Response({
            "count":   len(df),
            "results": df.where(pd.notna(df), other=None).to_dict(orient="records"),
        })


class CompanySnapshotView(APIView):
    """
    GET /api/snapshot/<company_id>/
    Returns the latest single-row snapshot for a company, combining
    company master + latest P&L + BS + CF data from CSVs.
    """

    def get(self, request, company_id: str):
        if not METRICS_CSV.exists():
            return Response({"error": "Run Phase 4 first."}, status=503)

        df = pd.read_csv(METRICS_CSV)
        co_df = pd.read_csv(METRICS_CSV.parent / "companies.csv")

        company_id = company_id.upper()
        rows = df[df["company_id"] == company_id].sort_values("year")

        if rows.empty:
            return Response({"error": f"Company '{company_id}' not found."}, status=404)

        latest   = rows.iloc[-1]
        co_row   = co_df[co_df["company_id"] == company_id]
        co_info  = co_row.iloc[0].to_dict() if not co_row.empty else {}

        def safe(val):
            return None if pd.isna(val) else val

        payload = {
            "company_id":        company_id,
            "company_name":      co_info.get("company_name"),
            "website":           co_info.get("website"),
            "nse_profile_url":   co_info.get("nse_profile"),
            "bse_profile_url":   co_info.get("bse_profile"),
            "company_logo_url":  co_info.get("company_logo_url"),
            "about_company":     co_info.get("about_company"),
            "face_value":        safe(co_info.get("face_value")),
            "book_value":        safe(co_info.get("book_value")),
            # Latest year metrics
            "latest_year":            safe(latest.get("year")),
            "latest_sales":           safe(latest.get("sales")),
            "latest_net_profit":      safe(latest.get("net_profit")),
            "net_profit_margin_pct":  safe(latest.get("net_profit_margin_pct")),
            "ebitda":                 safe(latest.get("ebitda")),
            "ebitda_margin_pct":      safe(latest.get("ebitda_margin_pct")),
            "opm_pct":                safe(latest.get("opm_pct")),
            "roe_pct":                safe(co_info.get("roe_pct")),
            "roce_pct":               safe(co_info.get("roce_pct")),
            "debt_to_equity":         safe(latest.get("debt_to_equity")),
            "interest_coverage":      safe(latest.get("interest_coverage")),
            "free_cash_flow":         safe(latest.get("free_cash_flow")),
            "operating_cash_ratio":   safe(latest.get("operating_cash_ratio")),
            "eps":                    safe(latest.get("eps")),
            "dividend_payout_pct":    safe(latest.get("dividend_payout_pct")),
            "sales_cagr_3y":          safe(latest.get("sales_cagr_3y")),
            "sales_cagr_5y":          safe(latest.get("sales_cagr_5y")),
            "profit_cagr_3y":         safe(latest.get("profit_cagr_3y")),
            "profit_cagr_5y":         safe(latest.get("profit_cagr_5y")),
            # Trend (all years)
            "trend": rows[[
                "year", "sales", "net_profit", "net_profit_margin_pct",
                "free_cash_flow", "debt_to_equity", "eps"
            ]].where(pd.notna(rows), other=None).to_dict(orient="records"),
        }

        return Response(payload)


class TopCompaniesView(APIView):
    """
    GET /api/top/?metric=roce_pct&limit=10
    Returns top N companies for a given metric (from metrics CSV).
    """
    ALLOWED_METRICS = [
        "net_profit_margin_pct", "opm_pct", "ebitda_margin_pct",
        "roe_derived_pct", "roce_derived_pct",
        "debt_to_equity", "free_cash_flow", "eps",
        "sales_cagr_5y", "profit_cagr_5y",
    ]

    def get(self, request):
        if not METRICS_CSV.exists():
            return Response({"error": "Run Phase 4 first."}, status=503)

        metric = request.query_params.get("metric", "net_profit_margin_pct")
        limit  = int(request.query_params.get("limit", 10))
        asc    = request.query_params.get("asc", "false").lower() == "true"

        if metric not in self.ALLOWED_METRICS:
            return Response(
                {"error": f"metric must be one of: {self.ALLOWED_METRICS}"},
                status=400
            )

        df = pd.read_csv(METRICS_CSV)
        # Latest year per company
        latest = df.sort_values("year").groupby("company_id").last().reset_index()
        ranked = (
            latest[["company_id", "year", metric]]
            .dropna(subset=[metric])
            .sort_values(metric, ascending=asc)
            .head(limit)
        )

        return Response({
            "metric":  metric,
            "count":   len(ranked),
            "results": ranked.where(pd.notna(ranked), other=None).to_dict(orient="records"),
        })
