# -*- coding: utf-8 -*-
"""

Configuration for the Sphinx documentation generator.

Reference: http://sphinx.pocoo.org/config.html

"""

import os
import sys

sys.path.insert(0, os.path.abspath('..'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'treebeard.tests.settings'

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage',
              'sphinx.ext.graphviz', 'sphinx.ext.inheritance_diagram',
              'sphinx.ext.todo']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = 'django-treebeard'
copyright = '2008-2013, Gustavo Picon'
version = '2.0b2'
release = '2.0b2'
exclude_trees = ['_build']
pygments_style = 'sphinx'
html_theme = 'default'
html_static_path = ['_static']
htmlhelp_basename = 'django-treebearddoc'
latex_documents = [(
    'index',
    'django-treebeard.tex',
    'django-treebeard Documentation',
    'Gustavo Picon',
    'manual')]
