try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

version = '0.1.4'

config = {
    'description': 'CarlCM',
    'author': 'Carl J Mackey',
    'url': 'https://github.com/cjmackey/carlcm',
    'author_email': 'carljmackey@gmail.com',
    'version': version,
    'install_requires': ['nose', 'mock', 'coverage',
                         'jinja2', 'pyfakefs', 'python-consul'],
    'packages': find_packages(),
    'scripts': ['bin/carlcm-counselor'],
    'name': 'carlcm',
    'classifiers': [
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Topic :: System :: Installation/Setup',
    ],
}

setup(**config)
