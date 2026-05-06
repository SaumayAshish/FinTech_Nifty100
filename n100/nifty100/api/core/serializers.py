from rest_framework import serializers

from .models import Analysis, BalanceSheet, CashFlow, Company, Document, MLScore, ProfitLoss, ProsCons


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["year_label", "document_url"]


class ProsConsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProsCons
        fields = ["is_pro", "category", "text", "source", "confidence", "generated_at"]


class CompanyListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "symbol",
            "company_name",
            "sector",
            "sub_sector",
            "website",
            "company_logo",
            "face_value",
            "book_value",
            "roce",
            "roe",
        ]


class CompanyDetailSerializer(serializers.ModelSerializer):
    documents = DocumentSerializer(many=True, read_only=True)
    pros_cons = ProsConsSerializer(many=True, read_only=True)

    class Meta:
        model = Company
        fields = "__all__"


class ProfitLossSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="symbol.company_name", read_only=True)
    year_label = serializers.CharField(source="year.year_label", read_only=True)

    class Meta:
        model = ProfitLoss
        fields = "__all__"


class BalanceSheetSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="symbol.company_name", read_only=True)
    year_label = serializers.CharField(source="year.year_label", read_only=True)

    class Meta:
        model = BalanceSheet
        fields = "__all__"


class CashFlowSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="symbol.company_name", read_only=True)
    year_label = serializers.CharField(source="year.year_label", read_only=True)

    class Meta:
        model = CashFlow
        fields = "__all__"


class AnalysisSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="symbol.company_name", read_only=True)

    class Meta:
        model = Analysis
        fields = "__all__"


class MLScoreSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="symbol.company_name", read_only=True)
    health_label_name = serializers.CharField(source="health_label.label_name", read_only=True)

    class Meta:
        model = MLScore
        fields = "__all__"


class SnapshotSerializer(serializers.Serializer):
    company = CompanyDetailSerializer()
    latest_profit_loss = ProfitLossSerializer(allow_null=True)
    latest_balance_sheet = BalanceSheetSerializer(allow_null=True)
    latest_cash_flow = CashFlowSerializer(allow_null=True)
    analysis = AnalysisSerializer(many=True)
    latest_ml_score = MLScoreSerializer(allow_null=True)
