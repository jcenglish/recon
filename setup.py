import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='recon-jcenglish',
    version='0.0.1',
    packages=[''],
    url='',
    license='',
    author='Jasmine English',
    author_email='contact@jasmineenglish.com',
    description='This program prints out the reconciliation between the account\'s transaction history and what the bank reports as the final positions for the day.',
    long_description=long_description,
    long_description_content_type="text/markdown",
)
