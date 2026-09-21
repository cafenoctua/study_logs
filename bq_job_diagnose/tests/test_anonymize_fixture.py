"""`scripts/anonymize_fixture.py` のテスト。

匿名化対象フィールドが確実に置き換わること、対象外フィールドが変更されない
ことの両方を確認する。
"""

from __future__ import annotations

import copy

from scripts.anonymize_fixture import anonymize_job_properties, anonymize_row


class TestAnonymizeRowInformationSchema:
    def _sample_row(self) -> dict:
        return {
            "job_id": "job_real_001",
            "project_id": "real-company-project",
            "user_email": "real.person@realcompany.com",
            "query": "SELECT ssn FROM sensitive_table WHERE id = 42",
            "referenced_tables": [
                {"project_id": "real-company-project", "dataset_id": "pii", "table_id": "users"}
            ],
            "destination_table": {
                "project_id": "real-company-project",
                "dataset_id": "pii",
                "table_id": "users_copy",
            },
            "labels": [{"key": "owner", "value": "alice"}],
            "state": "DONE",
            "total_slot_ms": 12345,
        }

    def test_user_email_is_replaced(self):
        out = anonymize_row(self._sample_row())
        assert out["user_email"] == "user@example.com"

    def test_project_id_is_replaced(self):
        out = anonymize_row(self._sample_row())
        assert out["project_id"] == "example-project"

    def test_query_is_replaced(self):
        out = anonymize_row(self._sample_row())
        assert out["query"] == "-- anonymized"
        assert "ssn" not in out["query"]

    def test_referenced_tables_are_replaced_with_dummy_names(self):
        out = anonymize_row(self._sample_row())
        assert out["referenced_tables"][0]["project_id"] == "example-project"
        assert "users" not in out["referenced_tables"][0]["table_id"]

    def test_destination_table_is_replaced(self):
        out = anonymize_row(self._sample_row())
        assert out["destination_table"]["project_id"] == "example-project"
        assert "users_copy" not in out["destination_table"]["table_id"]

    def test_labels_replaced_with_empty(self):
        out = anonymize_row(self._sample_row())
        assert out["labels"] == []

    def test_fields_not_in_the_anonymization_list_are_untouched(self):
        original = self._sample_row()
        out = anonymize_row(original)
        assert out["job_id"] == "job_real_001"
        assert out["state"] == "DONE"
        assert out["total_slot_ms"] == 12345

    def test_original_row_is_not_mutated(self):
        original = self._sample_row()
        original_copy = copy.deepcopy(original)
        anonymize_row(original)
        assert original == original_copy

    def test_none_values_are_left_as_none(self):
        row = {"user_email": None, "project_id": None, "query": None, "job_id": "x"}
        out = anonymize_row(row)
        assert out["user_email"] is None
        assert out["project_id"] is None
        assert out["query"] is None


class TestAnonymizeJobPropertiesRest:
    def _sample_properties(self) -> dict:
        return {
            "jobReference": {"jobId": "job_real_002", "projectId": "real-company-project"},
            "user_email": "real.person@realcompany.com",
            "configuration": {
                "labels": {"owner": "bob"},
                "query": {
                    "query": "SELECT * FROM secret",
                    "destinationTable": {
                        "projectId": "real-company-project",
                        "datasetId": "pii",
                        "tableId": "dest",
                    },
                },
            },
            "statistics": {
                "userEmail": "real.person@realcompany.com",
                "query": {
                    "referencedTables": [
                        {
                            "projectId": "real-company-project",
                            "datasetId": "pii",
                            "tableId": "src",
                        }
                    ]
                },
            },
        }

    def test_project_id_replaced_in_job_reference(self):
        out = anonymize_job_properties(self._sample_properties())
        assert out["jobReference"]["projectId"] == "example-project"

    def test_user_email_replaced_top_level_and_in_statistics(self):
        out = anonymize_job_properties(self._sample_properties())
        assert out["user_email"] == "user@example.com"
        assert out["statistics"]["userEmail"] == "user@example.com"

    def test_query_text_replaced(self):
        out = anonymize_job_properties(self._sample_properties())
        assert out["configuration"]["query"]["query"] == "-- anonymized"

    def test_labels_replaced_with_empty_object(self):
        out = anonymize_job_properties(self._sample_properties())
        assert out["configuration"]["labels"] == {}

    def test_referenced_tables_replaced(self):
        out = anonymize_job_properties(self._sample_properties())
        table = out["statistics"]["query"]["referencedTables"][0]
        assert table["projectId"] == "example-project"
        assert "src" not in table["tableId"]

    def test_job_id_untouched(self):
        out = anonymize_job_properties(self._sample_properties())
        assert out["jobReference"]["jobId"] == "job_real_002"
