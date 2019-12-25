# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""
See PEP 386 (https://www.python.org/dev/peps/pep-0386/)

Release logic:
 1. Remove ".devX" from __version__ (below)
 2. git add treebeard/__init__.py
 3. git commit -m 'Bump to <version>'
 4. git tag <version>
 5. git push
 6. assure that all tests pass on https://travis-ci.org/django-treebeard/django-treebeard/builds/
 7. git push --tags
 8. python setup.py sdist upload
 9. bump the version, append ".dev0" to __version__
10. git add treebeard/__init__.py
11. git commit -m 'Start with <version>'
12. git push
"""
__version__ = '4.3.1'
