import pytest

pytestmark = pytest.mark.django_db


def test_company_str(company):
    assert str(company) == "TCS - Tata Consultancy Services"


def test_profit_loss_unique_together(company, year, profit_loss):
    from django.db import IntegrityError

    from core.models import ProfitLoss

    with pytest.raises(IntegrityError):
        ProfitLoss.objects.create(symbol=company, year=year, sales=1)
