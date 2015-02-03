try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

config = {
    'description': 'CarlCM',
    'author': 'Carl J Mackey',
    'url': 'https://github.com/cjmackey/carlcm',
    'download_url': 'Where to download it.',
    'author_email': 'carljmackey@gmail.com',
    'version': '0.1',
    'install_requires': ['nose', 'mock', 'coverage', 'jinja2'],
    'packages': find_packages(),
    'scripts': [],
    'name': 'carlcm'
}

setup(**config)
