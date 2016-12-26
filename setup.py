try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

version = '0.1.16'

config = {
    'description': 'CarlCM',
    'author': 'Carl J Mackey',
    'url': 'https://github.com/cjmackey/carlcm',
    'author_email': 'carljmackey@gmail.com',
    'version': version,
    'install_requires': ['jinja2>=2', 'pyyaml>=3', 'requests>=2'],
    'packages': find_packages(),
    'scripts': [
        'bin/carlcm-bootstrap-council',
        'bin/carlcm-cluster-role',
        'bin/carlcm-counselor',
        'bin/carlcm-run-role',
    ],
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
