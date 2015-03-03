from setuptools import setup


def readreadme():
    with open('README.rst') as f:
        return f.read()

setup(name='geonear',
      version='0.1',
      description='Fas In-Memroy geoqueries with Redis',
      long_description=readreadme(),
      classifiers=[  # FIXME: adapt
          'Development Status :: 4 - Beta',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 2.7',
          'Topic :: Database :: Database Engines/Servers'
      ],
      keywords='geohash redis geoqueries db database',
      url='http://github.com/ihucos/geoqueries',
      author='Irae Hueck Costa',
      author_email='Irae Hueck Costa',
      license='MIT',
      packages=['geonear'],
      install_requires=[
          'requests',
          'python-geohash',
          # 'markdown',
      ],
      include_package_data=True,
      zip_safe=True)
