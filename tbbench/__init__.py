# -*- coding: utf-8 -*-
"""

   tbbench - Lies, damn lies, and benchmarks for treebeard
   -------------------------------------------------------

   :synopsys: Benchmarks for ``treebeard``
   :copyright: 2008 by Gustavo Picon
   :license: Apache License 2.0

   tbbench is a django app that isn't installed by default. I wrote it to find
   spots that could be optimized, and it may help you to tweak your database
   settings.

   To run the benchmarks:
      
      1. Add ``tbbench`` to your Python path
      2. Add ``'tbbench'`` to the ``INSTALLED_APPS`` section in your django
         settings file.
      3. Run :command:`python manage.py syncdb`
      4. In the ``tbbench`` dir, run :command:`python run.py`

   .. note::
       If the `django-mptt`_ package is also installed, both libraries will
       be tested with the exact same data an operations.

   Currently, the available tests are:

      1. Inserts: adds 1000 nodes to a tree, in different places: root
         nodes, normal nodes, leaf nodes
      2. Descendants: retrieves the full branch under every node several times.
      3. Move: moves nodes several times. This operation can be expensive
         because involves reodrering and data maintenance.
      4. Delete: Removes groups of nodes.

   For every available library (treebeard and mptt), two models are tested: a
   vanilla model, and a model with a "tree order by" attribute enabled
   (:attr:`~treebeard.MPNode.node_order_by` in treebeard,
   ``order_insertion_by`` in mptt).

   Also, every test will be tested with and without database transactions
   (``tx``).

   The output of the script is a reST table, with the time for every test in
   milliseconds (so small numbers are better).

   By default, these tests use the default tables created by ``syncdb``. Even
   when the results of ``treebeard`` are good, they can be improved *a lot*
   with better indexing. The Materialized Path Tree approach used by
   ``treebeard`` is *very* sensitive to database indexing, so you'll
   probably want to ``EXPLAIN`` your most common queries involving the
   :attr:`~treebeard.MPNode.path` field and add proper indexes.

   .. note::

    Tests results in Ubuntu 8.04.1 on a Thinkpad T61 with 4GB of ram.

    .. warning::

       These results shouldn't be taken as *"X is faster than Y"*,
       but as *"both X and Y are very fast"*.

    Databases tested:

     - MySQL InnoDB 5.0.51a, default settings
     - MySQL MyISAM 5.0.51a, default settings
     - PostgreSQL 8.2.7, default settings, mounted on RAM
     - PostgreSQL 8.3.3, default settings, mounted on RAM
     - SQLite3, mounted on RAM

    +-------------+-------------+-------------------+-------------------+-------------------+-------------------+-------------------+
    |  Test       | Model       |       innodb      |       myisam      |        pg82       |        pg83       |       sqlite      |
    |             |             +---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             |             |  no tx  |    tx   |  no tx  |    tx   |  no tx  |    tx   |  no tx  |    tx   |  no tx  |    tx   |
    +=============+=============+=========+=========+=========+=========+=========+=========+=========+=========+=========+=========+
    | Inserts     | TB          |    3050 |    2641 |    2665 |    2616 |    2954 |    2604 |    2482 |    2313 |    2138 |    1939 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT        |    7599 |    8021 |    4373 |    4465 |    5122 |   14074 |    4568 |    5950 |    3355 |    3061 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB Sorted   |    5015 |    4106 |    3670 |    3572 |    3913 |    5622 |    3306 |    3649 |    2946 |    2724 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT Sorted |   10033 |   10244 |    5226 |    5437 |    6058 |    9171 |    5517 |    7139 |    4611 |    4222 |
    +-------------+-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    | Descendants | TB          |    4007 |     N/A |    4040 |     N/A |    5540 |     N/A |    4868 |     N/A |    7663 |     N/A |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT        |    4941 |     N/A |    5001 |     N/A |    9294 |     N/A |    8764 |     N/A |    5193 |     N/A |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB Sorted   |    4101 |     N/A |    4115 |     N/A |    5785 |     N/A |    4945 |     N/A |    7808 |     N/A |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT Sorted |    5040 |     N/A |    4825 |     N/A |    9299 |     N/A |    8593 |     N/A |    5214 |     N/A |
    +-------------+-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    | Move        | TB          |     719 |     854 |     655 |     642 |     784 |    1067 |     617 |     747 |     482 |     476 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT        |    7136 |    5758 |    1220 |    1308 |    5103 |   18971 |    4581 |    9038 |     870 |     871 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB Sorted   |    6511 |    8038 |    3172 |    2858 |    6347 |   22646 |    3452 |   11860 |    2479 |    2387 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT Sorted |    6972 |    8280 |    1206 |    1433 |    5091 |   20346 |    4534 |   11981 |     945 |     913 |
    +-------------+-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    | Delete      | TB          |    2612 |    2243 |    2271 |    2257 |    2600 |    2413 |    2153 |    2064 |    2230 |    2065 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT        |    2943 |    4232 |    2729 |    3223 |   57766 |  187016 |   18426 |   25742 |    1630 |    1635 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB Sorted   |    2613 |    2415 |    2344 |    2248 |    2597 |    2628 |    2190 |    2320 |    2323 |    2092 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT Sorted |    3653 |    4467 |    2858 |    3964 |   67512 |  139179 |   64170 |  176193 |    1744 |    1813 |
    +-------------+-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+

   .. _`django-mptt`: http://code.google.com/p/django-mptt/

"""

