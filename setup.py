import subprocess
from os import path
from sysconfig import get_config_var

from setuptools import Extension, find_packages, setup
from setuptools.command.build import build
from setuptools.command.build_ext import build_ext
from setuptools.command.egg_info import egg_info
from wheel.bdist_wheel import bdist_wheel


def _ensure_parser():
    """Generate src/parser.c via the tree-sitter CLI if it is absent.

    This is required for source installations (e.g. VCS installs via pip/poetry)
    where the generated file is not committed to the repository.  Pre-built
    wheels already contain the compiled extension, so this path is never
    reached for normal binary installs.
    """
    if not path.exists("src/parser.c"):
        try:
            subprocess.run(["tree-sitter", "generate"], check=True)
        except FileNotFoundError:
            raise RuntimeError(
                "src/parser.c is missing and the tree-sitter CLI could not be "
                "found.  Install it (e.g. via npm or cargo) and re-run the build."
            )


class Build(build):
    def run(self):
        _ensure_parser()
        if path.isdir("queries"):
            dest = path.join(self.build_lib, "tree_sitter_org", "queries")
            self.copy_tree("queries", dest)
        super().run()


class BuildExt(build_ext):
    def build_extension(self, ext: Extension):
        if self.compiler.compiler_type != "msvc":
            ext.extra_compile_args = ["-std=c11", "-fvisibility=hidden"]
        else:
            ext.extra_compile_args = ["/std:c11", "/utf-8"]
        if path.exists("src/scanner.c"):
            ext.sources.append("src/scanner.c")
        if ext.py_limited_api:
            ext.define_macros.append(("Py_LIMITED_API", "0x030A0000"))
        super().build_extension(ext)


class BdistWheel(bdist_wheel):
    def get_tag(self):
        python, abi, platform = super().get_tag()
        if python.startswith("cp"):
            python, abi = "cp310", "abi3"
        return python, abi, platform


class EggInfo(egg_info):
    def run(self):
        _ensure_parser()
        super().run()

    def find_sources(self):
        super().find_sources()
        self.filelist.recursive_include("queries", "*.scm")
        self.filelist.include("src/tree_sitter/*.h")
        self.filelist.include("src/parser.c")
        self.filelist.include("src/scanner.c")


setup(
    packages=find_packages("bindings/python"),
    package_dir={"": "bindings/python"},
    package_data={
        "tree_sitter_org": ["*.pyi", "py.typed"],
        "tree_sitter_org.queries": ["*.scm"],
    },
    ext_package="tree_sitter_org",
    ext_modules=[
        Extension(
            name="_binding",
            sources=[
                "bindings/python/tree_sitter_org/binding.c",
                "src/parser.c",
            ],
            define_macros=[
                ("PY_SSIZE_T_CLEAN", None),
                ("TREE_SITTER_HIDE_SYMBOLS", None),
            ],
            include_dirs=["src"],
            py_limited_api=not get_config_var("Py_GIL_DISABLED"),
        )
    ],
    cmdclass={
        "build": Build,
        "build_ext": BuildExt,
        "bdist_wheel": BdistWheel,
        "egg_info": EggInfo,
    },
    zip_safe=False
)
