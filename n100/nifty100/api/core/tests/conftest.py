import pytest
from rest_framework.test import APIClient

from core.models import (
    BalanceSheet,
    Company,
    HealthLabel,
    MLScore,
    ProfitLoss,
    YearDimension,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def year(db):
    return YearDimension.objects.create(
        year_id=1,
        year_label="Mar 2024",
        fiscal_year=2024,
        quarter="Q4",
        sort_order=20244,
    )


@pytest.fixture
def company(db):
    return Company.objects.create(
        symbol="TCS",
        company_name="Tata Consultancy Services",
        sector="IT",
        sub_sector="IT Services",
        roce=45.5,
        roe=40.2,
    )


@pytest.fixture
def profit_loss(company, year):
    return ProfitLoss.objects.create(
        symbol=company,
        year=year,
        sales=100000,
        net_profit=20000,
        eps=55.5,
    )


@pytest.fixture
def balance_sheet(company, year):
    return BalanceSheet.objects.create(
        symbol=company,
        year=year,
        total_assets=500000,
        borrowings=50000,
        debt_to_equity=0.25,
    )


@pytest.fixture
def health_label(db):
    # sql/02_schema.sql seeds dim_health_label with the standard five labels.
    return HealthLabel.objects.get(label_name="EXCELLENT")


@pytest.fixture
def ml_score(company, health_label):
    from django.utils import timezone

    return MLScore.objects.create(
        symbol=company,
        computed_at=timezone.now(),
        overall_score=88.5,
        health_label=health_label,
    )
