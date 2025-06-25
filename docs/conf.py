import os
import sys
sys.path.insert(0, os.path.abspath('..'))

project = 'Laser Lens'
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.autosummary']
autosummary_generate = True
html_theme = 'alabaster'
