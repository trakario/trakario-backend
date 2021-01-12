from setuptools import setup

setup(
    name='trakario',
    version='0.1.0',
    description='Automatic job applicant tracking system',
    url='https://github.com/trakario/trakario',
    author='Matthew D. Scholefield',
    author_email='matthew331199@gmail.com',
    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='trakario',
    packages=['trakario'],
    install_requires=[
        'uvicorn',
        'fastapi',
        'loguru',
        'pydantic[dotenv]',

        'python-dateutil',
        'imap_tools',
        'spacy',

        'tortoise-orm[asyncpg]'
    ],
    entry_points={
        'console_scripts': [
            'trakario=trakario.__main__:main'
        ],
    }
)
