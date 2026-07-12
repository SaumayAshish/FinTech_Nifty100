import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_company_list(api_client, company):
    response = api_client.get(reverse("company-list"))
    assert response.status_code == 200
    symbols = [row["symbol"] for row in response.data["results"]]
    assert "TCS" in symbols


def test_company_list_search(api_client, company):
    response = api_client.get(reverse("company-list"), {"search": "Tata"})
    assert response.status_code == 200
    assert response.data["count"] == 1

    response = api_client.get(reverse("company-list"), {"search": "Nonexistent"})
    assert response.data["count"] == 0


def test_company_detail(api_client, company):
    response = api_client.get(reverse("company-detail", args=[company.symbol]))
    assert response.status_code == 200
    assert response.data["symbol"] == "TCS"
    assert response.data["documents"] == []
    assert response.data["pros_cons"] == []


def test_company_detail_not_found(api_client, db):
    response = api_client.get(reverse("company-detail", args=["NOPE"]))
    assert response.status_code == 404


def test_profit_loss_list_filters_by_symbol(api_client, profit_loss, company):
    response = api_client.get(reverse("profit-loss"), {"symbol": company.symbol})
    assert response.status_code == 200
    assert response.data["count"] == 1
    row = response.data["results"][0]
    assert row["company_name"] == company.company_name
    assert row["year_label"] == "Mar 2024"


def test_balance_sheet_list(api_client, balance_sheet, company):
    response = api_client.get(reverse("balance-sheet"), {"symbol": company.symbol})
    assert response.status_code == 200
    assert response.data["count"] == 1


def test_ml_score_list_includes_health_label(api_client, ml_score, company):
    response = api_client.get(reverse("ml-scores"))
    assert response.status_code == 200
    row = response.data["results"][0]
    assert row["health_label_name"] == "EXCELLENT"


def test_legacy_metrics_endpoint_matches_profit_loss(api_client, profit_loss, company):
    # /api/metrics/csv/ is a legacy URL alias for /api/financials/profit-loss/;
    # both must return identical DB-backed data (see LegacyMetricsView).
    legacy = api_client.get(reverse("metrics-csv"), {"symbol": company.symbol})
    current = api_client.get(reverse("profit-loss"), {"symbol": company.symbol})
    assert legacy.status_code == 200
    assert legacy.data["results"] == current.data["results"]


def test_snapshot_view_returns_404_for_unknown_company(api_client, db):
    response = api_client.get(reverse("snapshot", args=["NOPE"]))
    assert response.status_code == 404


def test_snapshot_view_returns_combined_data(
    api_client, company, profit_loss, balance_sheet, ml_score
):
    response = api_client.get(reverse("snapshot", args=[company.symbol]))
    assert response.status_code == 200
    assert response.data["company"]["symbol"] == "TCS"
    assert response.data["latest_profit_loss"]["net_profit"] == "20000.00"
    assert response.data["latest_balance_sheet"]["total_assets"] == "500000.00"
    assert response.data["latest_cash_flow"] is None
    assert response.data["analysis"] == []
    assert response.data["latest_ml_score"]["health_label_name"] == "EXCELLENT"
