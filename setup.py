import os
from setuptools import setup

f = open(os.path.join(os.path.dirname(__file__), 'README.rst'))
readme = f.read()
f.close()

setup(
    name='track-china-post-air-mail',
    version="1.0",
    description='ChinaPost / AirMail tracking GUI',
    long_description=readme,
    author="GoTLiuM InSPiRIT",
    author_email='gotlium@gmail.com',
    url='http://github.com/gotlium/track-china-post-air-mail',
    packages=['chinapostairmail'],
    include_package_data=True,
    install_requires=['setuptools', 'grab', 'antigate'],
    entry_points={
        'console_scripts': ['track = chinapostairmail:run']
    },
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: POSIX',
        'Programming Language :: Python',
    ],
)
