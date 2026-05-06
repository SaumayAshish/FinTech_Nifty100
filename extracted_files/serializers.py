from rest_framework import serializers
from .models import (
    Company, ProsAndCons, Document,
    ProfitLoss, BalanceSheet, CashFlow, FinancialMetrics
)


class ProsAndConsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ProsAndCons
        fields = ["id", "pros", "cons"]


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Document
        fields = ["id", "report_year", "annual_report_url"]


class CompanyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    class Meta:
        model  = Company
        fields = [
            "company_id", "company_name", "website",
            "nse_profile_url", "bse_profile_url",
            "company_logo_url", "book_value", "roce_pct", "roe_pct",
        ]


class CompanyDetailSerializer(serializers.ModelSerializer):
    """Full serializer with nested relations."""
    pros_cons = ProsAndConsSerializer(many=True, read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model  = Company
        fields = "__all__"


class ProfitLossSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.company_name", read_only=True)

    class Meta:
        model  = ProfitLoss
        fields = [
            "id", "company_id", "company_name", "date_key",
            "sales", "expenses", "operating_profit", "opm_pct",
            "other_income", "interest", "depreciation",
            "profit_before_tax", "tax_pct", "net_profit",
            "eps", "dividend_payout_pct", "ebitda", "net_profit_margin",
        ]


class BalanceSheetSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.company_name", read_only=True)

    class Meta:
        model  = BalanceSheet
        fields = [
            "id", "company_id", "company_name", "date_key",
            "equity_capital", "reserves", "borrowings", "other_liabilities",
            "total_liabilities", "fixed_assets", "cwip", "investments",
            "other_assets", "total_assets", "net_worth", "debt_to_equity",
        ]


class CashFlowSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.company_name", read_only=True)

    class Meta:
        model  = CashFlow
        fields = [
            "id", "company_id", "company_name", "date_key",
            "operating_activity", "investing_activity",
            "financing_activity", "net_cash_flow", "free_cash_flow",
        ]


class FinancialMetricsSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.company_name", read_only=True)

    class Meta:
        model  = FinancialMetrics
        fields = "__all__"


class CompanySnapshotSerializer(serializers.Serializer):
    """
    Combined one-call snapshot: company info + latest financials
    Built from raw data (no DB required if reading from CSVs).
    """
    company_id        = serializers.CharField()
    company_name      = serializers.CharField()
    roce_pct          = serializers.DecimalField(max_digits=6, decimal_places=2, allow_null=True)
    roe_pct           = serializers.DecimalField(max_digits=6, decimal_places=2, allow_null=True)
    book_value        = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    latest_year       = serializers.CharField(allow_null=True)
    latest_sales      = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)
    latest_net_profit = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)
    net_profit_margin = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    debt_to_equity    = serializers.DecimalField(max_digits=10, decimal_places=4, allow_null=True)
    free_cash_flow    = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)
    eps               = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
