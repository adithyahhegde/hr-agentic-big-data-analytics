from app.services.workload_router import ExecutionEngine, RoutingPolicy, WorkloadProfile, route_workload


def test_small_workload_uses_local_engine():
    profile = WorkloadProfile(row_count=10_000, column_count=30, estimated_bytes=5_000_000)
    assert route_workload(profile) is ExecutionEngine.LOCAL


def test_large_row_count_uses_spark():
    profile = WorkloadProfile(row_count=1_000_001, column_count=30)
    assert route_workload(profile) is ExecutionEngine.SPARK


def test_large_file_uses_spark():
    profile = WorkloadProfile(row_count=100_000, column_count=30, estimated_bytes=600 * 1024 * 1024)
    assert route_workload(profile) is ExecutionEngine.SPARK


def test_explicit_distributed_requirement_wins():
    profile = WorkloadProfile(row_count=100, column_count=5, requires_distributed=True)
    assert route_workload(profile) is ExecutionEngine.SPARK


def test_policy_is_configurable():
    profile = WorkloadProfile(row_count=10_001, column_count=5)
    policy = RoutingPolicy(max_local_rows=10_000)
    assert route_workload(profile, policy) is ExecutionEngine.SPARK
