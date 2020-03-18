from setuptools import setup, find_packages

setup(
    name='intermine_boot',
    version='0.0.2',
    license='LGPL',
    python_requires='>=3.5',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'gitpython',
        'xdg',
        'pyyaml'
    ],
    entry_points='''
        [console_scripts]
        intermine_boot=intermine_boot:cli
    ''',
    author='InterMine team',
    author_email='all@intermine.org',
    url='http://www.intermine.org',
    project_urls={
        'Bug Reports': 'https://github.com/intermine/intermine_boot/issues',
        'Source': 'https://github.com/intermine/intermine_boot',
    },
    keywords=['genomic', 'bioinformatics'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Library or '
        'Lesser General Public License (LGPL)',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Operating System :: OS Independent',
    ],
    description='A CLI tool to spin up local containers in which to build an InterMine.',
    long_description='''\
intermine_boot
--------------
A CLI tool to spin up local containers in which to build an InterMine.
'''
)
