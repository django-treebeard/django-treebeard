This is the documentation source for django-treebeard.
You can read the documentation on:

http://django-treebeard.readthedocs.io/en/latest/

Or create the documentation yourself by compiling the ReStructured Text files:

If you want to build the docs you'll need the graphviz tool, if you are using a Mac and Brew
you can install it like this:

$ brew install graphviz

Then you'll need at least Django and Sphinx:

$ pip install Django
$ pip install Sphinx

To build the docs run:

```bash
$ cd docs/
$ make html
```