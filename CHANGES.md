Release 4.9.0 (in development)
----------------------------
* Add support for Python 3.14.
* Add support for Django 6.0.
* Drop support for Django 5.1.
* Internal fields used by Treebeard's `MoveNodeForm` have been renamed from 
`_position` to `treebeard_position` and `_ref_node_id` to `treebeard_ref_node_id`.


Release 4.8.0 (Dec 3, 2025)
----------------------------
* Add support for Django 5.2, and Python 3.13.
* Drop support for Django 4.1 and 5.0.
* Refactor Django admin integration to be simpler, and more resilient to upstream changes.
* Add `include_self` option to `get_descendants` method.
* Fix KeyError in MP_Node.dump_bulk if ordering differs from depth, path.
* Exclude tests from packaged wheel distribution of django-treebeard


Release 4.7.1 (Jan 31, 2024)
----------------------------
* Fix: Allow usage of CSRF_COOKIE_HTTPONLY setting.
* Add support for Django-5.0.


Release 4.7 (Apr 7, 2023)
----------------------------

* Drop support for Django 4.0.
* Add support for Django 4.2.

Release 4.6.1 (Feb 5, 2023)
----------------------------

* Fix unescaped string representation of `AL_Node` models in the Django admin. 
  Thanks to goodguyandy for reporting the issue.
* Optimise `MP_Node.get_descendants` to avoid database queries when called on a leaf node.

Release 4.6 (Jan 2, 2023)
----------------------------

* Drop support for Django 3.1 and lower.
* Add support for Django 4.0 and 4.1.
* Drop support for Python 3.7 and lower.
* Add support for Python 3.10 and Python 3.11.
* Change the return value of `delete()` for all node classes to be consistent with Django,
  and return a tuple of the number of objects deleted and a dictionary with the number of 
  deletions per object type.
* Change the `delete()` methods for all node classes to accept arbitrary positional and 
  keyword arguments which are passed to the parent method.
* Set `alters_data` and `queryset_only` attributes on the `delete()` methods for all node classes
  to prevent them being used in an unwanted context (e.g., in Django templates).
* Drop dependency on jQuery UI in the admin.

Release 4.5.1 (Feb 22, 2021)
----------------------------

* Removed unnecessary default in MP's depth field.


Release 4.5 (Feb 17, 2021)
--------------------------

* Add support for custom primary key fields with custom names.
* Add support for Python 3.9.
* Add support for MSSQL 2019.
* Add Code of conduct
* Removed outdated Sqlite workaround code
* Remove last remains of Python 2.7 code
* Use Pytest-django and fixtures for testing


Release 4.4 (Jan 13, 2021)
----------------------------

* Implement a non-destructive path-fixing algorithm for `MP_Node.fix_tree`.
* Ensure `post_save` is triggered *after* the parent node is updated in `MP_AddChildHandler`.
* Fix static URL generation to use `static` template tag instead of constructing the URL manually.
* Declare support for Django 2.2, 3.0 and 3.1.
* Drop support for Django 2.1 and lower.
* Drop support for Python 2.7 and Python 3.5.
* Increase performance for `MoveNodeForm` when using large trees.


Release 4.3.1 (Dec 25, 2019)
----------------------------

* Added check to avoid unnecessary database query for `MP_Node.get_ancestors()`
  if the node is a root node.
* Drop support for Python-3.4.
* Play more nicely with other form classes, that implement `__init__(self, *args, **kwargs)`,
  e.g. django-parler's `TranslatableModelForm`, where `kwargs.get('instance')` is `None`
  when called from here.
* Sorting on path on necessary queries, fixes some issues and stabilizes the whole MP section.
* Add German translation strings.


Release 4.3 (Apr 16, 2018)
--------------------------

* Support for Django-2.0

Release 4.2.2 (Mar 11, 2018)
----------------------------

* Bugfix issues #97: UnboundLocalError raised on treebeard admin

Release 4.2.1 (Mar 9, 2018)
----------------------------

* Bugfix issues #90: admin change list view and jsi18n load for Django-1.11

Release 4.2.0 (Dec 8, 2017)
----------------------------

* Support for Django-2.0

Release 4.1.2 (Jun 22, 2017)
----------------------------

* Fixed MANIFEST.in for Debian packaging.


Release 4.1.1 (May 24, 2017)
----------------------------

* Removed deprecated templatetag inclusion
* Added support for Python-3.6
* Added support for MS-SQL


Release 4.1.0 (Nov 24, 2016)
----------------------------

* Add support for Django-1.10
* Drop support for Django-1.7
* Moved Repository from Bitbucket to GitHub
* Moved documentation to https://django-treebeard.readthedocs.io/
* Moved continuous integration to https://travis-ci.org/django-treebeard/django-treebeard


Release 4.0.1 (May 1, 2016)
---------------------------

* Escape input in forms (Martin Koistinen / Divio)
* Clarification on model detail pages (Michael Huang)

Release 4.0 (Dec 28, 2015)
--------------------------

* Added support for 3.5 and Django 1.7, 1.8 and 1.9
* Django 1.6 is no longer supported.
* Remove deprecated backports needed for now unsupported Django versions
* Fixed a bug with queryset deletion not handling inheritance correctly.
* Assorted documentation fixes


Release 3.0 (Jan 18, 2015)
--------------------------

* Limited tests (and hence support) to Python 2.7+/3.4+ and Django 1.6+
* Removed usage of deprecated Django functions.
* Fixed documentation issues.
* Fixed issues in MoveNodeForm
* Added get_annotated_list_qs and max_depth for get_annotated_list


Release 2.0 (April 2, 2014)
---------------------------

* Stable release.


Release 2.0rc2 (March, 2014)
----------------------------

* Support models that use multi-table inheritance (Matt Wescott)
* Tree methods called on proxy models should consistently return instances
  of that proxy model (Matt Wescott)


Release 2.0rc1 (February, 2014)
-------------------------------

* Fixed unicode related issue in the template tags.
* Major documentation cleanup.
* More warnings on the use of managers.
* Faster MP's is_root() method.


Release 2.0b2 (December, 2013)
------------------------------

* Dropped support for Python 2.5


Release 2.0b1 (May 29, 2013)
----------------------------

This is a beta release.

* Added support for Django 1.5 and Python 3.X
* Updated docs: the library supports python 2.5+ and Django 1.4+. Dropped
  support for older versions
* Revamped admin interface for MP and NS trees, supporting drag&drop to reorder
  nodes. Work on this patch was sponsored by the
  `Oregon Center for Applied Science`_, inspired by `FeinCMS`_ developed by
  `Jesús del Carpio`_ with tests from `Fernando Gutierrez`_. Thanks ORCAS!
* Updated setup.py to use distribute/setuptools instead of distutils
* Now using pytest for testing
* Small optimization to ns_tree.is_root
* Moved treebeard.tests to it's own directory (instead of tests.py)
* Added the runtests.py test runner
* Added tox support
* Fixed drag&drop bug in the admin
* Fixed a bug when moving MP_Nodes
* Using .pk instead of .id when accessing nodes.
* Removed the Benchmark (tbbench) and example (tbexample) apps.
* Fixed url parts join issues in the admin.
* Fixed: Now installing the static resources
* Fixed ManyToMany form field save handling
* In the admin, the node is now saved when moving so it can trigger handlers
  and/or signals.
* Improved translation files, including javascript.
* Renamed Node.get_database_engine() to Node.get_database_vendor(). As the name
  implies, it returns the database vendor instead of the engine used. Treebeard
  will get the value from Django, but you can subclass the method if needed.


Release 1.61 (Jul 24, 2010)
---------------------------

* Added admin i18n. Included translations: es, ru
* Fixed a bug when trying to introspect the database engine used in Django 1.2+
  while using new style db settings (DATABASES). Added
  Node.get_database_engine to deal with this.

Release 1.60 (Apr 18, 2010)
---------------------------

* Added get_annotated_list
* Complete revamp of the documentation. It's now divided in sections for easier
  reading, and the package includes .rst files instead of the html build.
* Added raw id fields support in the admin
* Fixed setup.py to make it work in 2.4 again
* The correct ordering in NS/MP trees is now enforced in the queryset.
* Cleaned up code, removed some unnecessary statements.
* Tests refactoring, to make it easier to spot the model being tested.
* Fixed support of trees using proxied models. It was broken due to a bug in
  Django.
* Fixed a bug in add_child when adding nodes to a non-leaf in sorted MP.
* There are now 648 unit tests. Test coverage is 96%
* This will be the last version compatible with Django 1.0. There will be a
  a 1.6.X branch maintained for urgent bug fixes, but the main development will
  focus on recent Django versions.


Release 1.52 (Dec 18, 2009)
---------------------------

* Really fixed the installation of templates.


Release 1.51 (Dec 16, 2009)
---------------------------

* Forgot to include treebeard/tempates/\*.html in MANIFEST.in


Release 1.5 (Dec 15, 2009)
--------------------------

New features added
~~~~~~~~~~~~~~~~~~

* Forms

  - Added MoveNodeForm

* Django Admin

  - Added TreeAdmin

* MP_Node

  - Added 2 new checks in MP_Node.find_problems():

    4. a list of ids of nodes with the wrong depth value for
       their path
    5. a list of ids nodes that report a wrong number of children

  - Added a new (safer and faster but less comprehensive) MP_Node.fix_tree()
    approach.

* Documentation

  - Added warnings in the documentation when subclassing MP_Node or NS_Node
    and adding a new Meta.

  - HTML documentation is now included in the package.

  - CHANGES file and section in the docs.

* Other changes:

  - script to build documentation

  - updated numconv.py


Bugs fixed
~~~~~~~~~~

* Added table quoting to all the sql queries that bypass the ORM.
  Solves bug in postgres when the table isn't created by syncdb.

* Removing unused method NS_Node._find_next_node

* Fixed MP_Node.get_tree to include the given parent when given a leaf node


Release 1.1 (Nov 20, 2008)
--------------------------

Bugs fixed
~~~~~~~~~~

* Added exceptions.py


Release 1.0 (Nov 19, 2008)
--------------------------

* First public release.


.. _Oregon Center for Applied Science: http://www.orcasinc.com/
.. _FeinCMS: http://www.feincms.org
.. _Jesús del Carpio: http://www.isgeek.net
.. _Fernando Gutierrez: http://xbito.pe
