from xyberos import DiagnosticReport, doctor


def test_doctor_returns_a_structured_runtime_snapshot():
    report = doctor()

    assert isinstance(report, DiagnosticReport)
    assert report.app_created is True
    assert report.kernel_started is False
    assert "config" in report.kernel_services
    assert "logger" in report.kernel_services
    assert "plugins" in report.kernel_services
    assert report.package_version
    assert report.python_version
    assert report.as_dict()["app_created"] is True
