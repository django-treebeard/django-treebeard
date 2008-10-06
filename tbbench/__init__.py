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
   (:attr:`~treebeard.MP_Node.node_order_by` in treebeard,
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
   :attr:`~treebeard.MP_Node.path` field and add proper indexes.

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

    +-------------+--------------+-------------------+-------------------+-------------------+-------------------+-------------------+
    | Test        | Model        |       innodb      |       myisam      |        pg82       |        pg83       |       sqlite      |
    |             |              +---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             |              |  no tx  |    tx   |  no tx  |    tx   |  no tx  |    tx   |  no tx  |    tx   |  no tx  |    tx   |
    +=============+==============+=========+=========+=========+=========+=========+=========+=========+=========+=========+=========+
    | Inserts     | TB MP        |    3194 |    2661 |    3210 |    2676 |    2958 |    2585 |    2515 |    2343 |    2257 |    1937 |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB AL        |    1976 |    1931 |    1941 |    1935 |    1940 |    1772 |    1749 |    1640 |    1554 |    1485 |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT         |    7030 |    9189 |    7015 |    9206 |    5213 |   16115 |    4657 |    9259 |    3532 |    3119 |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB MP Sorted |    4549 |    5532 |    4087 |    5731 |    3943 |    5638 |    3549 |    3845 |    3175 |    2895 |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB AL Sorted |    1308 |    1031 |    1077 |    1012 |    1182 |     988 |    1035 |     881 |     848 |     704 |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT Sorted  |    8055 |    9551 |    8113 |   10615 |    6117 |    8962 |    5563 |    6307 |    4636 |    4195 |
    +-------------+--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    | Descendants | TB MP        |    6245 |     N/A |    6377 |     N/A |    7822 |     N/A |    7168 |     N/A |   10652 |     N/A |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB AL        |   57767 |     N/A |   56616 |     N/A |   55590 |     N/A |   51321 |     N/A |   51235 |     N/A |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT         |    5332 |     N/A |    5344 |     N/A |    9603 |     N/A |    5439 |     N/A |    5382 |     N/A |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB MP Sorted |    6806 |     N/A |    6818 |     N/A |    8100 |     N/A |    7720 |     N/A |   10725 |     N/A |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB AL Sorted |   58547 |     N/A |   58055 |     N/A |   55914 |     N/A |   52505 |     N/A |   51991 |     N/A |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT Sorted  |    5163 |     N/A |    5443 |     N/A |    9661 |     N/A |    8930 |     N/A |    5192 |     N/A |
    +-------------+--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    | Move        | TB MP        |     874 |    1008 |     781 |    1131 |     756 |    1049 |     617 |     754 |     490 |     465 |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB AL        |    8870 |    8767 |    8833 |    8858 |    7263 |    7209 |    6842 |    6821 |    7187 |    7008 |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT         |    6222 |    7419 |    6505 |    7666 |    5270 |   22285 |    3383 |    7052 |     894 |     879 |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB MP Sorted |    7308 |    7026 |    6879 |    7312 |    6241 |   23016 |    3623 |   12396 |    2514 |    2451 |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB AL Sorted |    4046 |    3707 |    3959 |    3636 |    3570 |    3560 |    3409 |    3349 |    3671 |    3355 |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT Sorted  |    6943 |   11181 |    6646 |   10331 |    5060 |   18968 |    4650 |    8174 |     927 |     922 |
    +-------------+--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    | Delete      | TB MP        |     738 |     644 |     713 |     655 |     706 |     696 |     604 |     566 |     623 |     561 |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB AL        |     978 |    1085 |     987 |    1099 |     754 |     848 |     728 |     834 |     846 |     944 |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT         |    2839 |    4973 |    2902 |    3453 |   82047 |  148736 |   15706 |   21539 |    1648 |    1659 |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB MP Sorted |     813 |     757 |     875 |     737 |     932 |    1052 |     629 |     753 |     579 |     544 |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | TB AL Sorted |    1022 |    1007 |    1001 |     998 |     787 |     768 |     748 |     719 |     867 |     852 |
    |             +--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+
    |             | MPTT Sorted  |    4687 |    6370 |    4355 |    4112 |   58553 |  139216 |   15206 |  106658 |    1986 |    1743 |
    +-------------+--------------+---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+



   .. _`django-mptt`: http://code.google.com/p/django-mptt/

"""

