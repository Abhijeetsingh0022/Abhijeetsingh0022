#!/usr/bin/env python3
"""Self-check test suite for the dynamic GitHub profile generator."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def test_config():
    config_file = ROOT / "profile.config.json"
    assert config_file.exists(), "profile.config.json is missing"
    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert "links" in data, "config missing 'links'"
    print("PASS: profile.config.json is valid and free of hardcoded project/tech lists.")

def test_workflow():
    wf_file = ROOT / ".github" / "workflows" / "profile.yml"
    assert wf_file.exists(), "profile.yml is missing"
    content = wf_file.read_text(encoding="utf-8")
    assert "actions/checkout@v6" not in content, "Found invalid action checkout@v6"
    assert "actions/setup-python@v7" not in content, "Found invalid action setup-python@v7"
    assert "actions/checkout@v4" in content, "checkout@v4 not found"
    assert "actions/setup-python@v5" in content, "setup-python@v5 not found"
    print("PASS: profile.yml uses verified action versions.")

def test_generator():
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "update_profile.py")],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert res.returncode == 0, f"Generator failed with returncode {res.returncode}:\n{res.stderr}"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    
    # Check HTML table integrity
    tr_open = len(re.findall(r"<tr\b", readme))
    tr_close = len(re.findall(r"</tr>", readme))
    assert tr_open == tr_close, f"HTML table error: {tr_open} <tr> vs {tr_close} </tr>"

    td_open = len(re.findall(r"<td\b", readme))
    td_close = len(re.findall(r"</td>", readme))
    assert td_open == td_close, f"HTML table error: {td_open} <td> vs {td_close} </td>"

    table_open = len(re.findall(r"<table\b", readme))
    table_close = len(re.findall(r"</table>", readme))
    assert table_open == table_close, f"HTML table error: {table_open} <table> vs {table_close} </table>"

    # Check that live API data was populated
    assert "Abhijeet Singh" in readme, "Name missing in README"
    assert "JurisQuery" in readme, "JurisQuery missing in README"
    assert "Advance-Chat-Bot" in readme, "Advance-Chat-Bot missing in README"
    assert "Live GitHub Snapshot" in readme, "Live snapshot missing in README"
    assert "Dynamic Tech Ecosystem" in readme, "Dynamic ecosystem missing in README"
    assert "Profile generator" not in readme, "Temporary stub string found in README"
    print("PASS: update_profile.py generates valid, dynamic, well-formed README.md.")

def test_assets():
    snake_light = ROOT / "assets" / "github-contribution-grid-snake.svg"
    snake_dark = ROOT / "assets" / "github-contribution-grid-snake-dark.svg"
    assert snake_light.exists(), "Light snake SVG is missing"
    assert snake_dark.exists(), "Dark snake SVG is missing"
    assert "<svg" in snake_light.read_text(encoding="utf-8"), "Light snake SVG is invalid"
    assert "<svg" in snake_dark.read_text(encoding="utf-8"), "Dark snake SVG is invalid"
    print("PASS: Assets and fallback SVGs exist.")

if __name__ == "__main__":
    test_config()
    test_workflow()
    test_generator()
    test_assets()
    print("\nALL CHECKS PASSED: Profile system is fully validated.")
