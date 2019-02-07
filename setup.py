import os

from setuptools import setup, find_packages

from dynahost import __version__

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.rst')) as f:
    CHANGES = f.read()

requires = [
    'werkzeug',
    'requests',
    'html2text',
]

setup(name = 'dynahost',
    version = __version__,
    description = 'Web-service for maintainning Dynamic IP hosts',
    long_description = README + '\n\n' + CHANGES,
    author='Frédéric KIEBER',
    author_email = 'contact@frkb.fr',
    license = 'MIT',
    url = '',
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: French',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: System',
        'Topic :: System :: Networking',
    ],
    keywords = 'web-service dynahost dyndns',
    packages = find_packages(),
    include_package_data = True,
    zip_safe = False,
    install_requires = requires,
    entry_points = {
        'console_scripts' : [
            'dynahost = dynahost.service:main',
        ],
    },
    data_files = [('/etc/systemd/system', ['dynahost.service'])],
)
