"""Unit tests for Integrations Health Check & Connectivity Diagnostics."""

import os
import tempfile
from unittest.mock import MagicMock, patch

from health_check import (
    HealthReport,
    HealthStatus,
    ProbeResult,
    probe_finnhub,
    probe_nbp,
    render_health_markdown,
    run_health_check,
    run_probes,
    update_health_markdown_file,
)


def test_probe_result_to_dict():
    res = ProbeResult(
        id="test_service",
        name="Test Service",
        category="Test Category",
        auth_requirement="Public",
        status=HealthStatus.OK,
        latency_ms=123.45,
        endpoint_display="api.test.com",
        message="All good",
        troubleshooting="",
    )
    d = res.to_dict()
    assert d["id"] == "test_service"
    assert d["status"] == "OK"
    assert d["latency_ms"] == 123.45


def test_health_report_summary_and_all_ok():
    r1 = ProbeResult("s1", "S1", "Cat", "Auth", HealthStatus.OK, 50.0, "ep1", "ok")
    r2 = ProbeResult("s2", "S2", "Cat", "Auth", HealthStatus.WARN, None, "ep2", "warn")
    report = HealthReport(
        timestamp="2026-10-11 12:00:00",
        results=[r1, r2],
        total_probed=2,
        passed_count=1,
        warn_count=1,
        failed_count=0,
        all_ok=True,
        status_summary="1/2 Passed, 1 Warnings",
    )
    d = report.to_dict()
    assert d["all_ok"] is True
    assert d["failed_count"] == 0
    assert len(d["results"]) == 2


def test_run_probes_aggregation():
    def mock_ok(timeout):
        return ProbeResult("ok_svc", "OK Svc", "Cat", "Auth", HealthStatus.OK, 10.0, "ep", "ok")

    def mock_warn(timeout):
        return ProbeResult("warn_svc", "Warn Svc", "Cat", "Auth", HealthStatus.WARN, None, "ep", "warn")

    def mock_fail(timeout):
        return ProbeResult("fail_svc", "Fail Svc", "Cat", "Auth", HealthStatus.FAIL, 20.0, "ep", "fail")

    with patch.dict(
        "health_check.PROBES",
        {"ok_svc": mock_ok, "warn_svc": mock_warn, "fail_svc": mock_fail},
        clear=True,
    ):
        report = run_probes()
        assert report.total_probed == 3
        assert report.passed_count == 1
        assert report.warn_count == 1
        assert report.failed_count == 1
        assert report.all_ok is False
        assert "1/3 Passed, 1 Warnings, 1 Failed" in report.status_summary

        # Test selecting single probe
        single_report = run_probes(selected_ids=["ok_svc"])
        assert single_report.total_probed == 1
        assert single_report.all_ok is True
        assert single_report.passed_count == 1


def test_run_probes_handles_exception():
    def exploding_probe(timeout):
        raise RuntimeError("Network disconnected")

    with patch.dict("health_check.PROBES", {"boom": exploding_probe}, clear=True):
        report = run_probes()
        assert report.total_probed == 1
        assert report.failed_count == 1
        assert report.all_ok is False
        assert report.results[0].status == HealthStatus.FAIL
        assert "Unhandled probe error" in report.results[0].message


def test_render_health_markdown_and_file_update():
    r1 = ProbeResult("nbp", "NBP", "Macro", "Public", HealthStatus.OK, 250.0, "api.nbp.pl", "Reachable")
    report = HealthReport(
        timestamp="2026-10-11 15:30:00",
        results=[r1],
        total_probed=1,
        passed_count=1,
        warn_count=0,
        failed_count=0,
        all_ok=True,
        status_summary="1/1 Passed",
    )

    with tempfile.TemporaryDirectory() as tmp_vault:
        # Create minimal template directory in tmp_vault
        tmpl_dir = os.path.join(tmp_vault, "99_System", "Templates")
        os.makedirs(tmpl_dir, exist_ok=True)
        # Copy or point to real template
        script_dir = os.path.dirname(os.path.abspath(__file__))
        real_tmpl = os.path.abspath(os.path.join(script_dir, "../Templates/health_template.md"))
        with (
            open(real_tmpl, encoding="utf-8") as src,
            open(os.path.join(tmpl_dir, "health_template.md"), "w", encoding="utf-8") as dst,
        ):
            dst.write(src.read())

        rendered = render_health_markdown(report, target_vault=tmp_vault)
        assert "type: health_dashboard" in rendered
        assert "NBP" in rendered
        assert "250 ms" in rendered
        assert "dataviewjs" in rendered

        out_path = update_health_markdown_file(report, target_vault=tmp_vault)
        assert os.path.exists(out_path)
        with open(out_path, encoding="utf-8") as f:
            content = f.read()
        assert "type: health_dashboard" in content
        assert "1/1 Passed" in content


def test_run_health_check_exit_codes():
    ok_report = HealthReport(
        timestamp="2026-10-11 12:00:00",
        results=[],
        total_probed=1,
        passed_count=1,
        warn_count=0,
        failed_count=0,
        all_ok=True,
        status_summary="1/1 Passed",
    )
    fail_report = HealthReport(
        timestamp="2026-10-11 12:00:00",
        results=[],
        total_probed=1,
        passed_count=0,
        warn_count=0,
        failed_count=1,
        all_ok=False,
        status_summary="0/1 Passed, 1 Failed",
    )

    with patch("health_check.run_probes", return_value=ok_report):
        _, code = run_health_check(write_markdown=False)
        assert code == 0

    with patch("health_check.run_probes", return_value=fail_report):
        _, code = run_health_check(write_markdown=False)
        assert code == 1


def test_probe_nbp_mock():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"no": "199/A/NBP/2026", "rates": [{"mid": 4.28}]}]

    with patch("health_check._create_http_session") as mock_sess_factory:
        mock_sess = MagicMock()
        mock_sess.get.return_value = mock_resp
        mock_sess_factory.return_value = mock_sess

        res = probe_nbp(timeout=5.0)
        assert res.status == HealthStatus.OK
        assert res.id == "nbp"
        assert "199/A/NBP/2026" in res.message


def test_probe_finnhub_missing_key():
    with patch.dict(os.environ, {"FINNHUB_API_KEY": ""}, clear=False):
        res = probe_finnhub(timeout=5.0)
        assert res.status == HealthStatus.WARN
        assert "not configured" in res.message


def test_run_probes_skips_exante_in_csv_mode():
    def mock_ok(timeout):
        return ProbeResult("ok_svc", "OK Svc", "Cat", "Auth", HealthStatus.OK, 10.0, "ep", "ok")

    def mock_exante(timeout):
        return ProbeResult("exante", "Exante", "Broker", "Auth", HealthStatus.WARN, None, "ep", "warn")

    with tempfile.TemporaryDirectory() as tmp_vault:
        cfg_path = os.path.join(tmp_vault, "config.yaml")

        # 1. Exante in CSV mode -> skipped in general health probe
        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write('platforms:\n  exante:\n    enabled: true\n    default_mode: "csv"\n')

        with patch.dict("health_check.PROBES", {"ok_svc": mock_ok, "exante": mock_exante}, clear=True):
            report_csv = run_probes(target_vault=tmp_vault)
            probed_ids_csv = [r.id for r in report_csv.results]
            assert "ok_svc" in probed_ids_csv
            assert "exante" not in probed_ids_csv

            # Explicit --integration exante still runs
            report_explicit = run_probes(selected_ids=["exante"], target_vault=tmp_vault)
            assert [r.id for r in report_explicit.results] == ["exante"]

        # 2. Exante in API mode -> included in general health probe
        from model.config import load_vault_config

        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write('platforms:\n  exante:\n    enabled: true\n    default_mode: "api"\n')
        load_vault_config(base_dir=tmp_vault, force_refresh=True)

        with patch.dict("health_check.PROBES", {"ok_svc": mock_ok, "exante": mock_exante}, clear=True):
            report_api = run_probes(target_vault=tmp_vault)
            probed_ids_api = [r.id for r in report_api.results]
            assert "ok_svc" in probed_ids_api
            assert "exante" in probed_ids_api
