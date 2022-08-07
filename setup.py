import os
from glob import glob
from setuptools import find_namespace_packages, setup
from setuptools.command.build_py import build_py as _build_py


# From https://github.com/pypa/setuptools/pull/1574
class build_py(_build_py):
    def find_package_modules(self, package, package_dir):
        modules = super().find_package_modules(package, package_dir)
        patterns = self._get_platform_patterns(
            self.exclude_package_data,
            package,
            package_dir,
        )

        excluded_module_files = []
        for pattern in patterns:
            excluded_module_files.extend(glob(pattern))

        for f in excluded_module_files:
            for module in modules:
                if module[2] == f:
                    modules.remove(module)
        return modules

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='fiduswriter-ojs',
    version='3.10.6',
    packages=find_namespace_packages(),
    include_package_data=True,
    exclude_package_data={
        "": ["configuration.py", "django-admin.py", "build/*"]
    },
    license='AGPL License',
    description='A Fidus Writer plugin to connect to OJS.',
    long_description=README,
    long_description_content_type='text/markdown',
    url='https://www.fiduswriter.org/ojs-integration/',
    author='Johannes Wilm',
    author_email='johannes@fiduswriter.org',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 3.2',
        'Framework :: Django :: 4.0',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    cmdclass={'build_py': build_py}
)
