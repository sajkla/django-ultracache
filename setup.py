from setuptools import setup, find_packages

setup(
    name="django-ultracache",
    description="Drop-in replacement for Django's template fragment caching. Provides automatic cache invalidation.",
    long_description = open("README.rst", "r").read() + open("AUTHORS.rst", "r").read() + open("CHANGELOG.rst", "r").read(),
    version="2.1.0",
    author="Hedley Roos",
    author_email="hedleyroos@gmail.com",
    license="BSD",
    url="http://github.com/hedleyroos/django-ultracache",
    packages = find_packages(),
    dependency_links = [
    ],
    install_requires = [
        "django>=2.0",
        "requests",
        "pika>=0.11,<1.0",
        "PyYAML"
    ],
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    zip_safe=False,
)
