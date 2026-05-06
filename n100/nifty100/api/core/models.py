"""
Django ORM models for the Nifty 100 financial warehouse.

The tables are created by sql/02_schema.sql and loaded by the ETL scripts.
Models are unmanaged so Django can query the warehouse without owning DDL.
"""

from django.db import models


class Company(models.Model):
    symbol = models.CharField(max_length=20, primary_key=True)
    company_name = models.CharField(max_length=255)
    sector = models.CharField(max_length=100, blank=True, null=True)
    sub_sector = models.CharField(max_length=100, blank=True, null=True)
    company_logo = models.TextField(blank=True, null=True)
    website = models.TextField(blank=True, null=True)
    nse_url = models.TextField(blank=True, null=True)
    bse_url = models.TextField(blank=True, null=True)
    face_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    book_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    about_company = models.TextField(blank=True, null=True)
    roce = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    roe = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = "dim_company"
        managed = False
        ordering = ["symbol"]

    def __str__(self):
        return f"{self.symbol} - {self.company_name}"


class YearDimension(models.Model):
    year_id = models.IntegerField(primary_key=True)
    year_label = models.CharField(max_length=20, unique=True)
    fiscal_year = models.IntegerField(blank=True, null=True)
    quarter = models.CharField(max_length=4, blank=True, null=True)
    is_ttm = models.BooleanField(default=False)
    is_half_year = models.BooleanField(default=False)
    sort_order = models.IntegerField()

    class Meta:
        db_table = "dim_year"
        managed = False
        ordering = ["sort_order"]


class Sector(models.Model):
    sector_id = models.AutoField(primary_key=True)
    sector_name = models.CharField(max_length=100, unique=True)
    sector_code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "dim_sector"
        managed = False
        ordering = ["sector_name"]


class HealthLabel(models.Model):
    label_id = models.AutoField(primary_key=True)
    label_name = models.CharField(max_length=20, unique=True)
    min_score = models.DecimalField(max_digits=6, decimal_places=2)
    max_score = models.DecimalField(max_digits=6, decimal_places=2)
    color_hex = models.CharField(max_length=7)

    class Meta:
        db_table = "dim_health_label"
        managed = False
        ordering = ["min_score"]


class ProfitLoss(models.Model):
    symbol = models.ForeignKey(Company, on_delete=models.DO_NOTHING, db_column="symbol", related_name="profit_loss")
    year = models.ForeignKey(YearDimension, on_delete=models.DO_NOTHING, db_column="year_id", related_name="profit_loss")
    sales = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    expenses = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    operating_profit = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    opm_pct = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    other_income = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    interest = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    depreciation = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    profit_before_tax = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    tax_pct = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    net_profit = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    eps = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    dividend_payout_pct = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    net_profit_margin_pct = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    expense_ratio_pct = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    interest_coverage = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    asset_turnover = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    return_on_assets = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)

    class Meta:
        db_table = "fact_profit_loss"
        managed = False
        unique_together = [("symbol", "year")]
        ordering = ["symbol", "year"]


class BalanceSheet(models.Model):
    symbol = models.ForeignKey(Company, on_delete=models.DO_NOTHING, db_column="symbol", related_name="balance_sheet")
    year = models.ForeignKey(YearDimension, on_delete=models.DO_NOTHING, db_column="year_id", related_name="balance_sheet")
    equity_capital = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    reserves = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    borrowings = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    other_liabilities = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    total_liabilities = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    fixed_assets = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    cwip = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    investments = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    other_assets = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    total_assets = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    debt_to_equity = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    equity_ratio = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    book_value_per_share = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)

    class Meta:
        db_table = "fact_balance_sheet"
        managed = False
        unique_together = [("symbol", "year")]
        ordering = ["symbol", "year"]


class CashFlow(models.Model):
    symbol = models.ForeignKey(Company, on_delete=models.DO_NOTHING, db_column="symbol", related_name="cash_flow")
    year = models.ForeignKey(YearDimension, on_delete=models.DO_NOTHING, db_column="year_id", related_name="cash_flow")
    operating_activity = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    investing_activity = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    financing_activity = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    net_cash_flow = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    free_cash_flow = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    cash_conversion_ratio = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)

    class Meta:
        db_table = "fact_cash_flow"
        managed = False
        unique_together = [("symbol", "year")]
        ordering = ["symbol", "year"]


class Analysis(models.Model):
    symbol = models.ForeignKey(Company, on_delete=models.DO_NOTHING, db_column="symbol", related_name="analysis")
    period_label = models.CharField(max_length=10)
    compounded_sales_growth_pct = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    compounded_profit_growth_pct = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock_price_cagr_pct = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    roe_pct = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = "fact_analysis"
        managed = False
        unique_together = [("symbol", "period_label")]
        ordering = ["symbol", "period_label"]


class MLScore(models.Model):
    symbol = models.ForeignKey(Company, on_delete=models.DO_NOTHING, db_column="symbol", related_name="ml_scores")
    computed_at = models.DateTimeField()
    overall_score = models.DecimalField(max_digits=6, decimal_places=2)
    profitability_score = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    growth_score = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    leverage_score = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    cashflow_score = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    dividend_score = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    trend_score = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    health_label = models.ForeignKey(
        HealthLabel,
        on_delete=models.DO_NOTHING,
        db_column="health_label_id",
        related_name="ml_scores",
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "fact_ml_scores"
        managed = False
        ordering = ["-computed_at", "symbol"]


class ProsCons(models.Model):
    symbol = models.ForeignKey(Company, on_delete=models.DO_NOTHING, db_column="symbol", related_name="pros_cons")
    is_pro = models.BooleanField()
    category = models.CharField(max_length=100, blank=True, null=True)
    text = models.TextField()
    source = models.CharField(max_length=20, default="MANUAL")
    confidence = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    generated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "fact_pros_cons"
        managed = False
        ordering = ["symbol", "-is_pro"]


class Document(models.Model):
    symbol = models.ForeignKey(Company, on_delete=models.DO_NOTHING, db_column="symbol", related_name="documents")
    year_label = models.CharField(max_length=20, blank=True, null=True)
    document_url = models.TextField()

    class Meta:
        db_table = "documents"
        managed = False
        ordering = ["symbol", "year_label"]
