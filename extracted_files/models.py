"""
Django ORM models mirroring the PostgreSQL dw schema.
Models use db_table to map to existing schema tables.
"""
from django.db import models


class Company(models.Model):
    company_id       = models.CharField(max_length=30, primary_key=True)
    company_name     = models.TextField()
    website          = models.TextField(null=True, blank=True)
    nse_profile_url  = models.TextField(null=True, blank=True)
    bse_profile_url  = models.TextField(null=True, blank=True)
    company_logo_url = models.TextField(null=True, blank=True)
    about_company    = models.TextField(null=True, blank=True)
    face_value       = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    book_value       = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    roce_pct         = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    roe_pct          = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dim_company"
        managed  = False

    def __str__(self):
        return f"{self.company_id} — {self.company_name}"


class ProsAndCons(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                db_column="company_id", related_name="pros_cons")
    pros    = models.TextField(null=True, blank=True)
    cons    = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "dim_pros_cons"
        managed  = False


class Document(models.Model):
    company           = models.ForeignKey(Company, on_delete=models.CASCADE,
                                          db_column="company_id", related_name="documents")
    report_year       = models.SmallIntegerField(null=True)
    annual_report_url = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "dim_documents"
        managed  = False


class ProfitLoss(models.Model):
    company             = models.ForeignKey(Company, on_delete=models.CASCADE,
                                            db_column="company_id", related_name="profit_loss")
    date_key            = models.CharField(max_length=10)
    sales               = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    expenses            = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    operating_profit    = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    opm_pct             = models.DecimalField(max_digits=6,  decimal_places=2, null=True)
    other_income        = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    interest            = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    depreciation        = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    profit_before_tax   = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    tax_pct             = models.DecimalField(max_digits=6,  decimal_places=2, null=True)
    net_profit          = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    eps                 = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    dividend_payout_pct = models.DecimalField(max_digits=6,  decimal_places=2, null=True)
    ebitda              = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    net_profit_margin   = models.DecimalField(max_digits=8,  decimal_places=4, null=True)

    class Meta:
        db_table = "fact_profit_loss"
        managed  = False
        unique_together = [("company", "date_key")]


class BalanceSheet(models.Model):
    company           = models.ForeignKey(Company, on_delete=models.CASCADE,
                                          db_column="company_id", related_name="balance_sheets")
    date_key          = models.CharField(max_length=10)
    equity_capital    = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    reserves          = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    borrowings        = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    other_liabilities = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    total_liabilities = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    fixed_assets      = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    cwip              = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    investments       = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    other_assets      = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    total_assets      = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    net_worth         = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    debt_to_equity    = models.DecimalField(max_digits=10, decimal_places=4, null=True)

    class Meta:
        db_table = "fact_balance_sheet"
        managed  = False
        unique_together = [("company", "date_key")]


class CashFlow(models.Model):
    company            = models.ForeignKey(Company, on_delete=models.CASCADE,
                                           db_column="company_id", related_name="cash_flows")
    date_key           = models.CharField(max_length=10)
    operating_activity = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    investing_activity = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    financing_activity = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    net_cash_flow      = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    free_cash_flow     = models.DecimalField(max_digits=15, decimal_places=2, null=True)

    class Meta:
        db_table = "fact_cash_flow"
        managed  = False
        unique_together = [("company", "date_key")]


class FinancialMetrics(models.Model):
    company              = models.ForeignKey(Company, on_delete=models.CASCADE,
                                             db_column="company_id", related_name="metrics")
    date_key             = models.CharField(max_length=10)
    net_profit_margin    = models.DecimalField(max_digits=8,  decimal_places=4, null=True)
    opm_pct              = models.DecimalField(max_digits=6,  decimal_places=2, null=True)
    ebitda_margin        = models.DecimalField(max_digits=8,  decimal_places=4, null=True)
    roe_pct              = models.DecimalField(max_digits=6,  decimal_places=2, null=True)
    roce_pct             = models.DecimalField(max_digits=6,  decimal_places=2, null=True)
    debt_to_equity       = models.DecimalField(max_digits=10, decimal_places=4, null=True)
    interest_coverage    = models.DecimalField(max_digits=10, decimal_places=4, null=True)
    debt_to_assets       = models.DecimalField(max_digits=10, decimal_places=4, null=True)
    free_cash_flow       = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    operating_cash_ratio = models.DecimalField(max_digits=10, decimal_places=4, null=True)
    capex_intensity      = models.DecimalField(max_digits=8,  decimal_places=4, null=True)
    sales_growth_1y      = models.DecimalField(max_digits=8,  decimal_places=4, null=True)
    profit_growth_1y     = models.DecimalField(max_digits=8,  decimal_places=4, null=True)
    eps                  = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    dividend_payout_pct  = models.DecimalField(max_digits=6,  decimal_places=2, null=True)

    class Meta:
        db_table = "fact_metrics"
        managed  = False
        unique_together = [("company", "date_key")]
