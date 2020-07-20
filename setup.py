from setuptools import find_packages, setup

setup(
    name="taar_gcp_etl",
    use_scm_version=False,
    version="0.5.1",
    setup_requires=["setuptools_scm", "pytest-runner"],
    tests_require=["pytest"],
    include_package_data=True,
    packages=find_packages(exclude=["tests", "tests/*"]),
    description="Telemetry-Aware Addon Recommender ETL Tools",
    author="Mozilla Corporation",
    author_email="vng@mozilla.org",
    url="https://github.com/mozilla/taar_gcp_etl",
    license="MPL 2.0",
    install_requires=[],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment :: Mozilla",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    zip_safe=False,
)
