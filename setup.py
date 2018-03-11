from setuptools import setup

setup(name='d_jupyter_kernel',
      version='1.0',
      description='D kernel for Jupyter',
      author='Nikos Karagiannakis',
      author_email='nikoskaragiannakis@gmail.com',
      url='https://github.com/nikoskaragiannakis/d-jupyter-kernel/',
      download_url='https://github.com/nikoskaragiannakis/d-jupyter-kernel/tarball/1.0',
      packages=['d_jupyter_kernel'],
      scripts=['d_jupyter_kernel/install.py'],
      keywords=['jupyter', 'notebook', 'kernel', 'dlang', 'd'],
      include_package_data=True)
