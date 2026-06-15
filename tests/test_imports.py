from driftbench_core import evaluate, hash_turn


def test_exports_exist():
    assert callable(evaluate)
    assert callable(hash_turn)
