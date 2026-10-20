from app.service import patient_store, report_analysis_store


def test_report_analysis_history_is_persisted_and_scoped(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("PSYCONSULT_DATA_DIR", str(data_dir))
    monkeypatch.setenv("PSYCONSULT_DATABASE_PATH", str(data_dir / "test.sqlite3"))
    monkeypatch.setenv("PSYCONSULT_UPLOAD_DIR", str(data_dir / "uploads"))
    patient_store.init_database()

    user_id = "report-analysis-test-user"
    patient = patient_store.create_patient(
        user_id,
        {
            "patient_code": "REPORT-TEST-001",
            "display_name": "测试患者",
            "sex": "unknown",
            "birth_date": None,
            "notes": "",
        },
    )
    report = patient_store.create_report(
        user_id=user_id,
        patient_id=patient["id"],
        original_filename="assessment.pdf",
        content_type="application/pdf",
        size_bytes=100,
        storage_key="report-storage-key",
        sha256="a" * 64,
    )
    saved = report_analysis_store.create_analysis(
        user_id=user_id,
        patient_id=patient["id"],
        report_id=report["id"],
        extracted_text="PHQ-9 总分：8。该内容仅用于测试。",
        analysis_markdown="## 测试分析\n\n此结果不是临床诊断。",
        extraction_method="pdf_text",
        model_name="test-model",
    )
    assert saved["id"]
    assert saved["analysis_markdown"].startswith("## 测试分析")
    assert saved["extracted_text"].startswith("PHQ-9")

    history = report_analysis_store.list_analyses(user_id, patient["id"], report["id"])
    assert len(history) == 1
    assert history[0]["id"] == saved["id"]
    detail = report_analysis_store.get_analysis(
        user_id, patient["id"], report["id"], saved["id"]
    )
    assert detail is not None
    assert detail["extraction_method"] == "pdf_text"
    assert report_analysis_store.list_analyses(
        "another-user", patient["id"], report["id"]
    ) == []
