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
 8. pip install --upgrade pip wheel twine
 9. python setup.py clean --all
 9. python setup.py sdist bdist_wheel
10. twine upload dist/*
11. bump the version, append ".dev0" to __version__
12. git add treebeard/__init__.py
13. git commit -m 'Start with <version>'
14. git push
"""
__version__ = '4.5.1'
