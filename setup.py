from setuptools import setup

setup(
    name='rdio-gmusic',
    version='0.1',
    py_modules=['rdio_gmusic'],
    install_requires=[
        'click',
        'gmusicapi',
        'oauth2',
    ],
    entry_points='''
        [console_scripts]
        rdio-gmusic=rdio_gmusic:main
    ''',
)
