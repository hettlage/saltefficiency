from setuptools import setup

readme = file('README.md')
readme_text = ''
for line in readme:
    readme_text += line

setup(name='salt_efficiency',
      version='0.1',
      author='Paul Kotze',
      author_email='jpk@saao.ac.za',
      url='http://astronomer.salt.ac.za',
      description='SALT efficiency plots and reports',
      long_description=readme_text,
      packages=['saltefficiency', 'saltefficiency.nightly', 'saltefficiency.plot', 'saltefficiency.util'],
      install_requires=['MySQL-python', 'matplotlib', 'pandas'])