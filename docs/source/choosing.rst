Choosing a tree implementation
==============================

Treebeard provides four different tree implementations, each with the same API:

  1. :doc:`Adjacency List (AL) <al_tree>`: fast writes at the cost of slow reads. 
     Not appropriate for use cases where reads occur more often than writes.
  2. :doc:`Materialized Path (MP) <mp_tree>`: the most compatible and commonly used implementation.
  3. :doc:`Nested Sets (NS) <ns_tree>`: efficient reads at the cost of high maintenance on write/delete operations.
  4. :doc:`PostgreSQL Ltree (LT) <ltree>` (experimental): PostgreSQL-specific efficient tree implementation.

More details can be found on the documentation page for each implementation.

The table below illustrates the relative performance of each implementation for various operations. Actual
timings differ by database engine and system resources, so the data are only meaningful to compare the 
relative strengths of each tree implementation.

The code used to generate the benchmarks can be found in the source code at `tests/test_benchmarks.py`, which can be run with:

.. code-block:: bash

    TEST_BENCHMARKS=1 tox -- tests/test_benchmarks.py --benchmark-group-by func


.. csv-table::
   :header: Operation, AL,  NS, MP, LT

   Insertion: 100 nodes, **89ms**, 517ms, 263ms, 434ms
   Insertion: 100 nodes with `node_order_by` in random order, **40ms**, 1300ms, 1400ms, 1350ms
   Read: fetch all descendants of a root, 36ms, 10ms, **2ms**, **2ms**
   "Move: root to child, child to root", 47ms, 75ms, **23ms**, **18ms**
   Delete: delete a root and all descendants, 74ms, 57ms, **15ms**, **17ms**