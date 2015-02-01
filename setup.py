try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description': 'CarlCM',
    'author': 'Carl J Mackey',
    'url': 'https://github.com/cjmackey/carlcm',
    'download_url': 'Where to download it.',
    'author_email': 'carljmackey@gmail.com',
    'version': '0.1',
    'install_requires': ['nose', 'mock', 'coverage', 'jinja'],
    'packages': ['carlcm'],
    'scripts': [],
    'name': 'carlcm'
}

setup(**config)
