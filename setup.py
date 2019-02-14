import os

from setuptools import setup, find_packages

from dynahost import __version__

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.md')) as f:
    CHANGES = f.read()

requires = [
    'werkzeug',
    'requests',
    'html2text',
    'bcrypt',
]

setup(name = 'dynahost',
    version = __version__,
    description = 'Web-service pour administrer des hôtes en adresse IP dynamique',
    long_description = README + '\n\n' + CHANGES,
    long_description_content_type="text/markdown",
    author='Frédéric KIEBER',
    author_email = 'contact@frkb.fr',
    license = 'MIT',
    url = 'https://github.com/fkieber/dynahost',
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
    keywords = 'web-service dynhost dyndns ovh',
    packages = find_packages(),
    include_package_data = True,
    zip_safe = False,
    install_requires = requires,
    python_requires='>=3',
    entry_points = {
        'console_scripts' : [
            'dynahost = dynahost.service:main',
        ],
    },
    data_files = [('etc', ['dynahost.service', 'dynahost_config_sample.ini'])],
)
