# -*- coding: utf-8 -*-
"""

Configuration for the Sphinx documentation generator.

Reference: http://sphinx.pocoo.org/config.html

"""

import os
import sys
sys.path.append(os.path.abspath('..'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'django.conf.global_settings'
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage',
              'sphinx.ext.graphviz', 'sphinx.ext.inheritance_diagram',
              'sphinx.ext.todo']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = u'django-treebeard'
copyright = u'2008-2010, Gustavo Picon'
version = '2.0a1'
release = '2.0a1'
exclude_trees = ['_build']
pygments_style = 'sphinx'
html_theme = 'default'
html_static_path = ['_static']
htmlhelp_basename = 'django-treebearddoc'
latex_documents = [
  ('index', 'django-treebeard.tex', u'django-treebeard Documentation',
   u'Gustavo Picon', 'manual')]
