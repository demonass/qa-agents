import subprocess
import os
import json
import re
from langchain_core.tools import tool


@tool
def run_tests(test_path: str, test_framework: str = "pytest") -> str:
    """
    Run automated tests using specified framework.
    
    Args:
        test_path: Path to test file or directory
        test_framework: Test framework to use (pytest, unittest, nose)
    
    Returns:
        Test results as JSON string with summary and details
    """
    try:
        if test_framework == "pytest":
            result = _run_pytest(test_path)
        elif test_framework == "unittest":
            result = _run_unittest(test_path)
        elif test_framework == "nose":
            result = _run_nose(test_path)
        else:
            return json.dumps({"error": f"Unsupported framework: {test_framework}"})
        
        return json.dumps(result)
    
    except Exception as e:
        return json.dumps({"error": str(e)})


def _run_pytest(test_path: str) -> dict:
    """Run tests with pytest."""
    cmd = ["pytest", test_path, "-v", "--tb=short", "-rN"]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=os.getcwd()
    )
    
    return _parse_pytest_output(result.stdout, result.stderr, result.returncode)


def _run_unittest(test_path: str) -> dict:
    """Run tests with unittest."""
    cmd = ["python", "-m", "unittest", "discover", "-s", test_path, "-v"]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=os.getcwd()
    )
    
    return _parse_unittest_output(result.stdout, result.stderr, result.returncode)


def _run_nose(test_path: str) -> dict:
    """Run tests with nose."""
    cmd = ["nosetests", test_path, "-v"]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=os.getcwd()
    )
    
    return _parse_nose_output(result.stdout, result.stderr, result.returncode)


def _parse_pytest_output(stdout: str, stderr: str, returncode: int) -> dict:
    """Parse pytest output."""
    results = {
        "framework": "pytest",
        "success": returncode == 0,
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "duration": 0,
        "details": [],
        "raw_output": stdout + stderr
    }
    
    # Parse summary line like: "3 passed, 1 failed, 1 skipped in 0.52s"
    summary_match = re.search(r"(\d+) passed(?:, (\d+) failed)?(?:, (\d+) skipped)?(?:, (\d+) errors)? in ([\d.]+)s", stdout)
    if summary_match:
        results["passed"] = int(summary_match.group(1))
        results["failed"] = int(summary_match.group(2) or 0)
        results["skipped"] = int(summary_match.group(3) or 0)
        results["errors"] = int(summary_match.group(4) or 0)
        results["duration"] = float(summary_match.group(5))
        results["total"] = results["passed"] + results["failed"] + results["skipped"] + results["errors"]
    
    # Parse individual test results
    test_pattern = re.compile(r"(PASSED|FAILED|ERROR|SKIPPED)\s+(\S+)\s*\[(.+?)\]?", re.MULTILINE)
    for match in test_pattern.finditer(stdout):
        status = match.group(1)
        test_name = match.group(2)
        duration = match.group(3) if match.group(3) else ""
        
        results["details"].append({
            "test": test_name,
            "status": status,
            "duration": duration
        })
    
    return results


def _parse_unittest_output(stdout: str, stderr: str, returncode: int) -> dict:
    """Parse unittest output."""
    results = {
        "framework": "unittest",
        "success": returncode == 0,
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "duration": 0,
        "details": [],
        "raw_output": stdout + stderr
    }
    
    # Parse dots line and summary
    passed = stdout.count('.')
    failed = stdout.count('F')
    errors = stdout.count('E')
    skipped = stdout.count('s')
    
    results["passed"] = passed
    results["failed"] = failed
    results["errors"] = errors
    results["skipped"] = skipped
    results["total"] = passed + failed + errors + skipped
    
    # Parse duration
    duration_match = re.search(r"Ran (\d+) test[s]? in ([\d.]+)s", stdout)
    if duration_match:
        results["duration"] = float(duration_match.group(2))
    
    # Parse individual test names
    test_pattern = re.compile(r"(test_\w+)\s*\.\.\. (ok|FAIL|ERROR|skipped)", re.MULTILINE)
    for match in test_pattern.finditer(stdout):
        results["details"].append({
            "test": match.group(1),
            "status": match.group(2).upper()
        })
    
    return results


def _parse_nose_output(stdout: str, stderr: str, returncode: int) -> dict:
    """Parse nose output."""
    results = {
        "framework": "nose",
        "success": returncode == 0,
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "duration": 0,
        "details": [],
        "raw_output": stdout + stderr
    }
    
    # Parse summary
    summary_match = re.search(r"(\d+) test[s]? run in ([\d.]+)s", stdout)
    if summary_match:
        results["total"] = int(summary_match.group(1))
        results["duration"] = float(summary_match.group(2))
    
    # Count statuses
    results["passed"] = stdout.count("OK")
    results["failed"] = stdout.count("FAIL")
    results["errors"] = stdout.count("ERROR")
    results["skipped"] = stdout.count("SKIP")
    
    return results


@tool
def analyze_test_results(results_json: str) -> str:
    """
    Analyze test results and generate a comprehensive report.
    
    Args:
        results_json: JSON string from run_tests tool
    
    Returns:
        Human-readable analysis report
    """
    try:
        results = json.loads(results_json)
        
        if "error" in results:
            return f"❌ Test execution failed: {results['error']}"
        
        passed_rate = (results["passed"] / results["total"]) * 100 if results["total"] > 0 else 0
        
        report = f"""
📊 Test Execution Report
========================

Basic Information:
- Framework: {results['framework']}
- Total Tests: {results['total']}
- Duration: {results['duration']:.2f} seconds

Results Summary:
- ✅ Passed: {results['passed']}
- ❌ Failed: {results['failed']}
- ⚠️ Errors: {results['errors']}
- ⏭️ Skipped: {results['skipped']}
- 📈 Pass Rate: {passed_rate:.1f}%

Status: {'✅ All tests passed!' if results['success'] else '❌ Some tests failed'}
"""
        
        if results["details"]:
            report += "\n\nDetailed Results:\n"
            report += "-" * 40 + "\n"
            for detail in results["details"]:
                status_icon = "✅" if detail["status"] == "PASSED" else \
                             "❌" if detail["status"] == "FAILED" else \
                             "⚠️" if detail["status"] == "ERROR" else "⏭️"
                report += f"{status_icon} {detail['test']}"
                if "duration" in detail and detail["duration"]:
                    report += f" ({detail['duration']})"
                report += "\n"
        
        if not results["success"]:
            report += "\n💡 Recommendations:\n"
            report += "- Review failed tests for bugs\n"
            report += "- Check error messages for root causes\n"
            report += "- Fix failing assertions\n"
        
        return report.strip()
    
    except Exception as e:
        return f"❌ Failed to analyze results: {str(e)}"


@tool
def generate_test_summary(results_json: str) -> str:
    """
    Generate a concise test summary for reporting.
    
    Args:
        results_json: JSON string from run_tests tool
    
    Returns:
        Concise summary string
    """
    try:
        results = json.loads(results_json)
        
        if "error" in results:
            return f"Test failed: {results['error']}"
        
        passed_rate = (results["passed"] / results["total"]) * 100 if results["total"] > 0 else 0
        
        return f"Test Summary: {results['passed']}/{results['total']} passed ({passed_rate:.1f}%), {results['failed']} failed, {results['duration']:.2f}s"
    
    except Exception as e:
        return f"Failed to generate summary: {str(e)}"
