# #ai-assisted — generated with Claude and Codex LLM with human supervision.
# Adapted from stc/scripts/score_architecture.py for the Encryptor project.
"""Automated architecture scorecard for the Encryptor repository.

This script evaluates eight dimensions and renders either a table or JSON
payload suitable for CI automation.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

NESTING_NODES = (
    ast.If,
    ast.For,
    ast.While,
    ast.With,
    ast.Try,
    ast.AsyncFor,
    ast.AsyncWith,
)

# --- Limits (tuneable per-project) ----------------------------------------

MAX_FILE_LINES = 400
MAX_FUNC_LINES = 50
WARN_FUNC_LINES = 30
MAX_NESTING_DEPTH = 4


@dataclass
class DimensionResult:
    """Score output for a single architecture dimension."""

    name: str
    score: int
    detail: str
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.score >= 8:
            return "PASS"
        if self.score >= 5:
            return "WARN"
        return "FAIL"


# --- Helpers ---------------------------------------------------------------


def _iter_python_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts and ".venv" not in path.parts
    )


def _max_nesting_depth(node: ast.AST, current: int = 0) -> int:
    max_depth = current
    for child in ast.iter_child_nodes(node):
        if isinstance(child, NESTING_NODES):
            max_depth = max(max_depth, _max_nesting_depth(child, current + 1))
        else:
            max_depth = max(max_depth, _max_nesting_depth(child, current))
    return max_depth


def _count_for_loop_test_patterns(tests_dir: Path) -> int:
    count = 0
    for py_file in sorted(tests_dir.rglob("test_*.py")):
        if py_file.name == "test_score.py":
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                if any(isinstance(child, (ast.For, ast.AsyncFor)) for child in ast.walk(node)):
                    count += 1
    return count


def _count_parametrize_decorators(tests_dir: Path) -> int:
    count = 0
    for py_file in sorted(tests_dir.rglob("test_*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for decorator in node.decorator_list:
                if "parametrize" in ast.unparse(decorator):
                    count += 1
    return count


def _signature_annotation_count(py_file: Path) -> int:
    """Count ``dict[str, Any]`` / ``Dict[str, Any]`` in function signatures."""
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        annotations = [node.returns]
        annotations.extend(arg.annotation for arg in node.args.args)
        annotations.extend(arg.annotation for arg in node.args.kwonlyargs)
        if node.args.vararg and node.args.vararg.annotation:
            annotations.append(node.args.vararg.annotation)
        if node.args.kwarg and node.args.kwarg.annotation:
            annotations.append(node.args.kwarg.annotation)
        for annotation in annotations:
            if annotation is None:
                continue
            rendered = ast.unparse(annotation)
            count += rendered.count("dict[str, Any]")
            count += rendered.count("Dict[str, Any]")
    return count


def _can_import_package(repo_root: Path) -> bool:
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import encryptor"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


# --- Dimensions ------------------------------------------------------------


def score_readability(pkg_dir: Path) -> DimensionResult:
    violations: list[str] = []
    warnings: list[str] = []
    score = 10
    oversized_files = 0
    long_functions = 0
    deep_functions = 0
    missing_docstrings = 0

    for py_file in _iter_python_files(pkg_dir):
        source = py_file.read_text(encoding="utf-8")
        lines = source.splitlines()
        if len(lines) > MAX_FILE_LINES:
            oversized_files += 1
            violations.append(f"{py_file}: {len(lines)} lines (>{MAX_FILE_LINES})")
        tree = ast.parse(source, filename=str(py_file))
        if not ast.get_docstring(tree):
            missing_docstrings += 1
            violations.append(f"{py_file}: missing module docstring")
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_len = (node.end_lineno or node.lineno) - node.lineno + 1
                if func_len > WARN_FUNC_LINES:
                    warnings.append(f"{py_file}:{node.lineno} {node.name}() {func_len} lines")
                if func_len > MAX_FUNC_LINES:
                    long_functions += 1
                    violations.append(
                        f"{py_file}:{node.lineno} {node.name}() "
                        f"{func_len} lines (>{MAX_FUNC_LINES})"
                    )
                depth = _max_nesting_depth(node)
                if depth > MAX_NESTING_DEPTH:
                    deep_functions += 1
                    violations.append(
                        f"{py_file}:{node.lineno} {node.name}() "
                        f"nesting depth {depth} (>{MAX_NESTING_DEPTH})"
                    )

    score -= 2 * oversized_files
    score -= math.ceil(long_functions / 5) if long_functions else 0
    score -= deep_functions
    score -= missing_docstrings

    detail = (
        f"{oversized_files} files >{MAX_FILE_LINES} LOC, "
        f"{long_functions} funcs >{MAX_FUNC_LINES} LOC, "
        f"{deep_functions} funcs nesting >{MAX_NESTING_DEPTH}, "
        f"{missing_docstrings} missing module docstrings"
    )
    return DimensionResult("Readability", max(0, score), detail, violations, warnings)


def score_modularity(pkg_dir: Path, repo_root: Path) -> DimensionResult:
    violations: list[str] = []
    score = 10

    # __init__.py should only contain version / re-exports
    init_file = pkg_dir / "__init__.py"
    if init_file.exists():
        init_tree = ast.parse(init_file.read_text(encoding="utf-8"), filename=str(init_file))
        disallowed: list[ast.stmt] = []
        for node in init_tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                continue
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = {t.id for t in targets if isinstance(t, ast.Name)}
                if names & {"__all__", "__version__"}:
                    continue
            disallowed.append(node)
        if disallowed:
            score -= 3
            violations.append("__init__.py contains executable logic beyond re-exports")
    else:
        score -= 2
        violations.append("encryptor/__init__.py is missing")

    # Expect separate modules for crypto, fileops, cli
    expected_modules = ["crypto.py", "fileops.py", "cli.py"]
    for mod in expected_modules:
        if not (pkg_dir / mod).exists():
            score -= 2
            violations.append(f"encryptor/{mod} is missing")

    if not _can_import_package(repo_root):
        score -= 3
        violations.append("import encryptor failed (possible circular import or package breakage)")

    detail = (
        f"{len(expected_modules)} expected modules, "
        f"__init__.py {'clean' if not violations else 'has issues'}"
    )
    return DimensionResult("Modularity", max(0, score), detail, violations)


def score_security(pkg_dir: Path) -> DimensionResult:
    """Security-specific checks for a cryptography tool."""
    violations: list[str] = []
    warnings: list[str] = []
    score = 10

    crypto_file = pkg_dir / "crypto.py"
    if crypto_file.exists():
        source = crypto_file.read_text(encoding="utf-8")
        # Must use os.urandom or secrets, not random
        if "import random" in source:
            score -= 3
            violations.append("crypto.py imports stdlib random (use os.urandom)")
        # Must use PBKDF2 with sufficient iterations
        iter_match = re.search(r"PBKDF2_ITERATIONS.*?=\s*(\d[\d_]*)", source)
        if iter_match:
            iterations = int(iter_match.group(1).replace("_", ""))
            if iterations < 100_000:
                score -= 2
                violations.append(f"PBKDF2 iterations = {iterations} (minimum 100,000)")
        else:
            score -= 1
            warnings.append("Could not detect PBKDF2 iteration count constant")
        # Must use Fernet or authenticated encryption
        if "Fernet" not in source and "AESGCM" not in source:
            score -= 2
            violations.append("crypto.py does not use authenticated encryption (Fernet/AESGCM)")
    else:
        score -= 5
        violations.append("crypto.py is missing")

    fileops_file = pkg_dir / "fileops.py"
    if fileops_file.exists():
        source = fileops_file.read_text(encoding="utf-8")
        # Key files must be created with restricted permissions
        if "0o600" not in source and "0600" not in source:
            score -= 2
            violations.append("fileops.py does not set key file permissions to 0o600")
    else:
        score -= 2
        violations.append("fileops.py is missing")

    # Scan all files for hardcoded secrets patterns
    secret_patterns = re.compile(
        r"""(password|secret|key)\s*=\s*['"][^'"]{8,}['"]""", re.IGNORECASE
    )
    for py_file in _iter_python_files(pkg_dir):
        source = py_file.read_text(encoding="utf-8")
        for match in secret_patterns.finditer(source):
            line = source[: match.start()].count("\n") + 1
            score -= 2
            violations.append(
                f"{py_file}:{line} possible hardcoded secret: {match.group()[:40]}..."
            )

    detail = f"{len(violations)} security issues"
    return DimensionResult("Security", max(0, score), detail, violations, warnings)


def score_test_quality(tests_dir: Path, repo_root: Path) -> DimensionResult:
    violations: list[str] = []
    warnings: list[str] = []
    score = 10

    # Coverage gate in pyproject.toml
    pyproject = repo_root / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8")
        cov_match = re.search(r"cov-fail-under[=\s]+(\d+)", text)
        coverage_gate = int(cov_match.group(1)) if cov_match else 0
    else:
        coverage_gate = 0
    if coverage_gate < 100:
        score -= 3
        violations.append(f"Coverage fail-under is {coverage_gate}, expected 100")

    if not tests_dir.exists():
        score -= 5
        violations.append("tests/ directory is missing")
        return DimensionResult("Test Quality", max(0, score), "no tests directory", violations)

    if not (tests_dir / "conftest.py").exists():
        score -= 1
        violations.append("tests/conftest.py is missing")

    # Test file count vs module count
    test_file_count = len(list(tests_dir.glob("test_*.py")))
    pkg_dir = repo_root / "encryptor"
    module_count = len([p for p in _iter_python_files(pkg_dir) if p.name != "__init__.py"])
    if module_count > 0 and test_file_count < module_count:
        score -= 1
        violations.append(f"Only {test_file_count} test files for {module_count} modules")

    for_loop_patterns = _count_for_loop_test_patterns(tests_dir)
    if for_loop_patterns:
        score -= min(2, for_loop_patterns)
        violations.append(f"{for_loop_patterns} test functions contain for-loop patterns")

    parametrize_count = _count_parametrize_decorators(tests_dir)
    ratio = f"{test_file_count}/{module_count}" if module_count else f"{test_file_count}/0"
    detail = (
        f"coverage gate {coverage_gate}%, "
        f"test/module ratio {ratio}, "
        f"{parametrize_count} parametrize, "
        f"{for_loop_patterns} for-loop patterns"
    )
    return DimensionResult("Test Quality", max(0, score), detail, violations, warnings)


def score_documentation(repo_root: Path, pkg_dir: Path) -> DimensionResult:
    violations: list[str] = []
    score = 10

    # README must exist and have substance
    readme = repo_root / "README.md"
    if not readme.exists():
        score -= 3
        violations.append("README.md is missing")
    elif len(readme.read_text(encoding="utf-8").splitlines()) < 5:
        score -= 2
        violations.append("README.md is too short (<5 lines)")

    # Module docstrings
    missing_docstrings = 0
    for py_file in _iter_python_files(pkg_dir):
        if py_file.name == "__init__.py":
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        if not ast.get_docstring(tree):
            missing_docstrings += 1
            score -= 1
            violations.append(f"{py_file}: missing module docstring")

    # CLAUDE.md / AGENTS.md
    if not (repo_root / "CLAUDE.md").exists():
        score -= 1
        violations.append("CLAUDE.md is missing")

    detail = f"{missing_docstrings} modules missing docstrings"
    return DimensionResult("Documentation", max(0, score), detail, violations)


def score_build_packaging(repo_root: Path) -> DimensionResult:
    violations: list[str] = []
    score = 10

    # pyproject.toml must exist with build-system
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        score -= 4
        violations.append("pyproject.toml is missing")
    else:
        text = pyproject.read_text(encoding="utf-8")
        if "[build-system]" not in text:
            score -= 2
            violations.append("pyproject.toml missing [build-system]")
        if "[project.scripts]" not in text:
            score -= 1
            violations.append("pyproject.toml missing [project.scripts] entry point")
        if "[dependency-groups]" not in text and "[project.optional-dependencies]" not in text:
            score -= 1
            violations.append("pyproject.toml missing dev dependency group")

    # Makefile must exist with key targets
    makefile = repo_root / "Makefile"
    if not makefile.exists():
        score -= 3
        violations.append("Makefile is missing")
    else:
        text = makefile.read_text(encoding="utf-8")
        for target in ["test", "lint", "format", "clean"]:
            if f"{target}:" not in text:
                score -= 1
                violations.append(f"Makefile missing '{target}' target")

    # uv.lock should be present
    if not (repo_root / "uv.lock").exists():
        score -= 1
        violations.append("uv.lock is missing (run uv sync)")

    if not _can_import_package(repo_root):
        score -= 2
        violations.append("import encryptor failed")

    detail = (
        f"pyproject {'present' if pyproject.exists() else 'missing'}, "
        f"Makefile {'present' if makefile.exists() else 'missing'}, "
        f"uv.lock {'present' if (repo_root / 'uv.lock').exists() else 'missing'}"
    )
    return DimensionResult("Build & Packaging", max(0, score), detail, violations)


def score_type_safety(pkg_dir: Path) -> DimensionResult:
    violations: list[str] = []
    score = 10

    total_dict_any = sum(_signature_annotation_count(f) for f in _iter_python_files(pkg_dir))
    score = max(0, int(10 - (total_dict_any / 5)))
    if total_dict_any:
        violations.append(f"{total_dict_any} dict[str, Any] signature annotations remain")

    # Check for missing return type annotations
    missing_annotations = 0
    for py_file in _iter_python_files(pkg_dir):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name.startswith("_") and node.name != "__init__":
                continue
            if node.returns is None:
                missing_annotations += 1
                violations.append(f"{py_file}:{node.lineno} {node.name}() missing return type")
    if missing_annotations:
        score -= min(3, missing_annotations)

    detail = (
        f"{total_dict_any} dict[str, Any] in signatures, "
        f"{missing_annotations} public funcs missing return types"
    )
    return DimensionResult("Type Safety", max(0, score), detail, violations)


def score_code_duplication(pkg_dir: Path) -> DimensionResult:
    violations: list[str] = []
    score = 10

    # Check for duplicate function names across modules
    function_names: dict[str, list[str]] = {}
    for py_file in _iter_python_files(pkg_dir):
        if py_file.name == "__init__.py":
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                function_names.setdefault(node.name, []).append(str(py_file))

    duplicates = {name: locs for name, locs in function_names.items() if len(locs) > 1}
    for name, locs in duplicates.items():
        score -= 2
        violations.append(f"Duplicate function '{name}' in {', '.join(locs)}")

    # Check for large files that may need splitting
    for py_file in _iter_python_files(pkg_dir):
        lines = len(py_file.read_text(encoding="utf-8").splitlines())
        if lines > 300:
            score -= 1
            violations.append(f"{py_file}: {lines} lines — consider splitting")

    detail = f"{len(duplicates)} duplicate function names"
    return DimensionResult("Code Duplication", max(0, score), detail, violations)


# --- Scorecard rendering ---------------------------------------------------


def calculate_overall(results: list[DimensionResult]) -> float:
    if not results:
        return 0.0
    return round(sum(r.score for r in results) / len(results), 1)


def render_scorecard(results: list[DimensionResult], verbose: bool = False) -> str:
    headers = ("Dimension", "Score", "Status", "Details")
    rows = [(r.name, f"{r.score}/10", r.status, r.detail) for r in results]
    widths = [
        max(len(headers[i]), max((len(str(row[i])) for row in rows), default=0)) for i in range(4)
    ]
    border = "-" * (sum(widths) + 9)
    lines = [
        "Encryptor Architecture Scorecard",
        border,
        (
            f"{headers[0]:<{widths[0]}}  "
            f"{headers[1]:<{widths[1]}}  "
            f"{headers[2]:<{widths[2]}}  "
            f"{headers[3]}"
        ),
        border,
    ]
    for r in results:
        lines.append(
            f"{r.name:<{widths[0]}}  "
            f"{f'{r.score}/10':<{widths[1]}}  "
            f"{r.status:<{widths[2]}}  "
            f"{r.detail}"
        )
    lines.extend([border, f"OVERALL  {calculate_overall(results):.1f}/10"])

    if verbose:
        for r in results:
            if r.violations or r.warnings:
                lines.append("")
                lines.append(f"[{r.name}]")
                lines.extend(f"- {v}" for v in r.violations)
                lines.extend(f"- warning: {w}" for w in r.warnings)
    else:
        needs_work = sum(1 for r in results if r.score < 8)
        if needs_work:
            lines.append("")
            lines.append(
                f"{needs_work} dimensions need work. Run with --verbose for file-level details."
            )
    return "\n".join(lines)


def _json_payload(results: list[DimensionResult], min_score: int) -> str:
    dimensions = {
        r.name.lower().replace(" & ", "_").replace(" ", "_"): {
            "score": r.score,
            "status": r.status,
            "detail": r.detail,
            "violations": r.violations,
            "warnings": r.warnings,
        }
        for r in results
    }
    payload = {
        "overall": calculate_overall(results),
        "dimensions": dimensions,
        "pass": all(r.score >= min_score for r in results),
        "min_score": min_score,
    }
    return json.dumps(payload, indent=2, sort_keys=True)


# --- Entrypoint ------------------------------------------------------------


def run_scorecard(repo_root: Path, selected_dimension: str | None = None) -> list[DimensionResult]:
    pkg_dir = repo_root / "encryptor"
    tests_dir = repo_root / "tests"
    scorers: dict[str, Callable[[], DimensionResult]] = {
        "readability": lambda: score_readability(pkg_dir),
        "modularity": lambda: score_modularity(pkg_dir, repo_root),
        "security": lambda: score_security(pkg_dir),
        "test_quality": lambda: score_test_quality(tests_dir, repo_root),
        "documentation": lambda: score_documentation(repo_root, pkg_dir),
        "build_packaging": lambda: score_build_packaging(repo_root),
        "type_safety": lambda: score_type_safety(pkg_dir),
        "code_duplication": lambda: score_code_duplication(pkg_dir),
    }
    if selected_dimension is not None:
        key = selected_dimension.lower().replace("-", "_")
        if key not in scorers:
            valid = ", ".join(k.replace("_", "-") for k in scorers)
            raise ValueError(f"Unknown dimension: {selected_dimension}. Valid dimensions: {valid}")
        return [scorers[key]()]
    return [scorer() for scorer in scorers.values()]


def main(argv: list[str] | None = None, repo_root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description="Encryptor architecture scorecard")
    parser.add_argument("--verbose", action="store_true", help="Show file-level details")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of table output")
    parser.add_argument(
        "--min-score",
        type=int,
        default=0,
        help="Exit 1 if any dimension scores below this threshold",
    )
    parser.add_argument(
        "--dimension",
        help=(
            "Score a single dimension: readability, modularity, security, "
            "test-quality, documentation, build-packaging, type-safety, "
            "code-duplication"
        ),
    )
    args = parser.parse_args(argv)
    root = repo_root or Path(__file__).resolve().parents[1]
    results = run_scorecard(root, args.dimension)
    if args.json:
        print(_json_payload(results, args.min_score))
    else:
        print(render_scorecard(results, verbose=args.verbose))
    return 0 if all(r.score >= args.min_score for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
