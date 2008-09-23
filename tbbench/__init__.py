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

       These results shouldn't be taken as *"treebeard is faster than mptt"*,
       but as *"treebeard can be as fast as mptt"*.

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
    | Inserts     | TB          |    5048 |    2809 |    2851 |    2729 |    2719 |    2456 |    2805 |    2622 |    2558 |    1916 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB Sorted   |    5592 |    3797 |    4020 |    3884 |    3672 |    5529 |    3692 |    4004 |    3434 |    2693 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT        |   11413 |    7948 |    4665 |    4757 |    4811 |    7418 |    5128 |    7535 |    4531 |    3241 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT Sorted |   10941 |   10476 |    5628 |    5770 |    6018 |    8934 |    6147 |    7391 |    5707 |    4672 |
    +-------------+-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    | Descendants | TB          |    4148 |    4347 |    4224 |    4138 |    5276 |    7049 |    5550 |    5760 |    7572 |    7703 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB Sorted   |    4237 |    4222 |    4280 |    4229 |    5512 |   18143 |    5608 |    8945 |    7763 |    7670 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT        |    5008 |    4911 |    4879 |    4911 |    9259 |   25998 |    9394 |   15051 |    7549 |    7503 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT Sorted |    4987 |    5090 |    4901 |    5073 |    9645 |    9952 |    9365 |   14439 |    7486 |    7475 |
    +-------------+-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    | Move        | TB          |    1192 |    1105 |    1040 |    1002 |     707 |     968 |     656 |     748 |     531 |     465 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB Sorted   |   13144 |   12352 |    6629 |    6219 |    6027 |   16768 |    3370 |   11991 |    2461 |    2285 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT        |    7528 |    8728 |    1364 |    1507 |    5200 |   24582 |    2948 |    6642 |    1064 |     954 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT Sorted |    8222 |    7517 |    1404 |    1726 |    5449 |   25704 |    4894 |    7524 |    1074 |     993 |
    +-------------+-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    | Delete      | TB          |    3640 |    2326 |    2498 |    2424 |    2421 |    2323 |    2979 |    2261 |    2691 |    2105 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB Sorted   |    3546 |    2514 |    2509 |    2378 |    2497 |    2774 |    2394 |    2513 |    2727 |    2270 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT        |    3199 |    3629 |    3383 |    4077 |  104545 |   20930 |   14227 |   19003 |    1630 |    1612 |
    |             +-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT Sorted |    3791 |    3757 |    3582 |    4479 |  100987 |  193881 |   69445 |   60807 |    1780 |    1831 |
    +-------------+-------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+

   .. _`django-mptt`: http://code.google.com/p/django-mptt/

"""

