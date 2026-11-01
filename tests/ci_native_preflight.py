"""Tight real-platform ownership and recovery regressions before matrix expansion."""


def load_tests(loader, tests, pattern):
    tests.addTests(
        loader.loadTestsFromNames(
            (
                "tests.test_partition_session_ownership",
                "tests.test_partition_session_reader",
                "tests.test_partition_hash_execution.HashExecution.test_source_name_aba_rejects_when_python_ctime_reports_creation_time",
                "tests.test_partition_hash_execution.HashExecution.test_native_metadata_stamp_uses_change_time_not_creation_time",
                "tests.test_partition_hash_execution.HashExecution.test_native_metadata_time_rejects_source_and_snapshot_name_aba",
                "tests.test_partition_hash_execution.HashExecution.test_windows_directory_pin_prevents_directory_rename",
                "tests.test_partition_hash_execution.HashExecution.test_windows_guard_requests_directory_data_access_for_delete_sharing",
            )
        )
    )
    return tests
