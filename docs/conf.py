import os
import sys
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../laser_lens'))

project = 'Laser Lens'
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.autosummary']
autosummary_generate = True
html_theme = 'alabaster'
autodoc_mock_imports = ['streamlit', 'laser_lens.ui_main']
suppress_warnings = ['toc.not_included', 'autodoc.mocked_object']
