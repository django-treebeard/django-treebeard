import os
from random import randint

import pytest
from django.db import connection

from tests import models


@pytest.fixture(scope="function", params=models.BENCHMARK_MODELS)
def benchmark_model(request):
    return request.param


@pytest.fixture(scope="function", params=models.SORTED_MODELS)
def sorted_model(request):
    return request.param


def create_nodes(cls):
    """
    Creates a tree with 5 root nodes, each with 19 descendants in a deep tree.
    """
    roots = []
    for i in range(5):
        roots.append(cls.add_root({"desc": f"root-{i}"}))

    for root in roots:
        depth = 1
        node = root
        while depth < 20:
            node = node.add_child({"desc": f"{root.desc}-child-{depth}"})
            depth += 1


def create_sorted_nodes(cls):
    """
    Creates a tree with 5 root nodes, each with 19 children in a flat tree,
    """
    roots = []
    for i in range(5):
        roots.append(cls.add_root({"desc": f"root-{i}", "val1": randint(0, 100), "val2": randint(0, 100)}))

    for root in roots:
        for n in range(20):
            root.add_child({"desc": f"{root.desc}-child-{n}", "val1": randint(0, 100), "val2": randint(0, 100)})


def get_descendants(cls):
    """
    Get an entire subtree.
    """
    list(cls.objects.get(desc="root-2").get_descendants())


def move(cls):
    """
    Moves:
    - A root node to a deeply nested child
    - A child node to the root
    """
    root = cls.objects.get(desc="root-1")
    child = cls.objects.get(desc="root-2-child-18")
    cls.objects.move(root, child, "first-sibling")

    child = cls.objects.get(desc="root-3-child-18")
    root = cls.objects.get(desc="root-2")
    cls.objects.move(child, root, "first-sibling")


def move_sorted(cls):
    root = cls.objects.get(desc="root-1")
    child = cls.objects.get(desc="root-2-child-18")
    cls.objects.move(root, child, "sorted-sibling")


def delete(cls):
    """
    Deletes:
    - One root node
    - One descendant node
    """
    cls.objects.get(desc="root-3-child-7").delete()
    cls.objects.get(desc="root-1").delete()


def teardown(cls):
    # Truncate table between rounds
    # This is preferable to deleting all rows which leads to GC issues on some backends
    cursor = connection.cursor()
    if connection.vendor == "sqlite":
        cursor.execute(f"DELETE FROM {cls._meta.db_table};")
    else:
        cursor.execute(f"TRUNCATE TABLE {cls._meta.db_table} CASCADE;")


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(not os.environ.get("TEST_BENCHMARKS"), reason="Skipping benchmarks")
class TestBenchmarks:
    def test_create(self, benchmark_model, benchmark):
        benchmark.pedantic(create_nodes, args=[benchmark_model], rounds=10, teardown=teardown)

    def test_create_sorted(self, sorted_model, benchmark):
        benchmark.pedantic(create_sorted_nodes, args=[sorted_model], rounds=10, teardown=teardown)

    def test_get_descendants(self, benchmark_model, benchmark):
        def setup():
            create_nodes(benchmark_model)

        benchmark.pedantic(get_descendants, args=[benchmark_model], rounds=10, teardown=teardown, setup=setup)

    def test_move(self, benchmark_model, benchmark):
        def setup():
            create_nodes(benchmark_model)

        benchmark.pedantic(move, args=[benchmark_model], rounds=10, teardown=teardown, setup=setup)

    def test_move_sorted(self, sorted_model, benchmark):
        def setup():
            create_sorted_nodes(sorted_model)

        benchmark.pedantic(move_sorted, args=[sorted_model], rounds=10, teardown=teardown, setup=setup)

    def test_delete(self, benchmark_model, benchmark):
        def setup():
            create_nodes(benchmark_model)

        benchmark.pedantic(delete, args=[benchmark_model], rounds=10, teardown=teardown, setup=setup)
