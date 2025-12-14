#!/usr/bin/env python3
"""
Dev-only helper that runs a lightweight Giskard scan on the job-matching RAG flow.

Usage:
    python core/tests/run_giskard_scan.py

Optional flags:
    --upload        Upload scan results to a running Giskard server (requires
                    GISKARD_URL and GISKARD_API_KEY to be set).
    --project-key   Override the remote project key (default: hirewire-ai-job-matching).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List

try:
    import pandas as pd
except Exception as exc:  # pragma: no cover - dev convenience guard
    raise SystemExit("pandas is required for the Giskard scan. Install via pip.") from exc

try:
    import giskard
except Exception as exc:  # pragma: no cover - dev convenience guard
    raise SystemExit("giskard is required. Install via `pip install giskard`.") from exc


# Add parent directory to path to allow importing core.api when running from core/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.api import rag

FIXTURE_PATH = Path(__file__).parent / "giskard_fixtures" / "job_matching_cases.json"


def _load_cases() -> List[dict]:
    if not FIXTURE_PATH.exists():
        raise SystemExit(f"Fixture file missing: {FIXTURE_PATH}")
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise SystemExit("Fixture JSON must contain a list of cases.")
    return data


def _ensure_embedding_keys() -> None:
    provider = rag.EMBEDDING_PROVIDER.lower()
    if provider == "fireworks" and not rag.FIREWORKS_API_KEY:
        raise SystemExit("Set FIREWORKS_API_KEY before running the Giskard scan.")
    if provider == "openai" and not rag.OPENAI_API_KEY:
        raise SystemExit("Set OPENAI_API_KEY before running the Giskard scan.")


def _score_job_match(cv_text: str) -> str:
    chunks = rag.chunk_text(cv_text)
    if not chunks:
        raise RuntimeError("Empty CV text encountered in fixture.")
    embedding = rag.embed_text(" ".join(chunks))
    jobs = rag.search_similar_jobs(embedding, top_n=5)
    return rag.generate_answer(cv_text, jobs)


def _build_model():
    def _predict(df: "pd.DataFrame") -> List[str]:
        outputs: List[str] = []
        for _, row in df.iterrows():
            outputs.append(_score_job_match(row["cv_text"]))
        return outputs

    return giskard.Model(
        model=_predict,
        model_type="text_generation",
        feature_names=["cv_text"],
        name="Job matching RAG",
    )


def _build_dataset(cases: List[dict]):
    df = pd.DataFrame(cases)
    # Only keep the cv_text column for the scan, drop metadata columns
    df = df[["cv_text"]]
    return giskard.Dataset(
        df,
        column_types={"cv_text": "text"},
        target=None,
        name="Job matching fixtures",
    )


def _build_client(upload: bool):
    if not upload:
        return None
    url = os.getenv("GISKARD_URL")
    api_key = os.getenv("GISKARD_API_KEY")
    if not url or not api_key:
        raise SystemExit("Set GISKARD_URL and GISKARD_API_KEY to upload scan results.")
    return giskard.GiskardClient(url=url, api_key=api_key)


def _generate_html_report(scan, output_path: Path) -> None:
    """Generate an HTML report from scan results."""
    issues = getattr(scan, "issues", [])
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Giskard Scan Report - Job Matching RAG</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.2s;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        .stat-number {{
            font-size: 3em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .stat-label {{
            color: #6c757d;
            font-size: 1.1em;
        }}
        .success {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .danger {{ color: #dc3545; }}
        .info {{ color: #17a2b8; }}
        .content {{
            padding: 40px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h2 {{
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        .issue-card {{
            background: #fff;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .issue-card.high {{
            border-left-color: #dc3545;
            background: #fff5f5;
        }}
        .issue-card.medium {{
            border-left-color: #ffc107;
            background: #fffbf0;
        }}
        .issue-card.low {{
            border-left-color: #17a2b8;
            background: #f0f9ff;
        }}
        .issue-title {{
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }}
        .issue-description {{
            color: #555;
            line-height: 1.6;
            margin-bottom: 10px;
        }}
        .severity-badge {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .severity-high {{ background: #dc3545; color: white; }}
        .severity-medium {{ background: #ffc107; color: #333; }}
        .severity-low {{ background: #17a2b8; color: white; }}
        .no-issues {{
            text-align: center;
            padding: 60px 20px;
            background: #f0f9ff;
            border-radius: 8px;
        }}
        .no-issues-icon {{
            font-size: 5em;
            margin-bottom: 20px;
        }}
        .no-issues h3 {{
            color: #28a745;
            font-size: 2em;
            margin-bottom: 10px;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #6c757d;
            border-top: 1px solid #dee2e6;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Giskard Scan Report</h1>
            <p>Job Matching RAG Quality Assessment</p>
        </div>
        
        <div class="summary">
            <div class="stat-card">
                <div class="stat-number {'success' if len(issues) == 0 else 'warning'}">{len(issues)}</div>
                <div class="stat-label">Total Issues</div>
            </div>
            <div class="stat-card">
                <div class="stat-number danger">{len([i for i in issues if getattr(i, 'severity', '').upper() == 'HIGH'])}</div>
                <div class="stat-label">High Severity</div>
            </div>
            <div class="stat-card">
                <div class="stat-number warning">{len([i for i in issues if getattr(i, 'severity', '').upper() == 'MEDIUM'])}</div>
                <div class="stat-label">Medium Severity</div>
            </div>
            <div class="stat-card">
                <div class="stat-number info">{len([i for i in issues if getattr(i, 'severity', '').upper() == 'LOW'])}</div>
                <div class="stat-label">Low Severity</div>
            </div>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>Scan Results</h2>
                {''.join([f'''<div class="issue-card {getattr(i, 'severity', 'low').lower()}">
                    <div class="issue-title">{getattr(i, 'name', 'Unknown Issue')}</div>
                    <div class="issue-description">{getattr(i, 'description', 'No description available')}</div>
                    <span class="severity-badge severity-{getattr(i, 'severity', 'low').lower()}">{getattr(i, 'severity', 'LOW')}</span>
                </div>''' for i in issues]) if issues else '<div class="no-issues"><div class="no-issues-icon">✅</div><h3>All Clear!</h3><p>No issues detected in your model. Great job!</p></div>'}
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by Giskard v2.0 • {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""
    
    output_path.write_text(html_content, encoding="utf-8")
    print(f"\n📊 HTML report saved to: {output_path.absolute()}")


def run_scan(upload: bool, project_key: str, html_report: bool = False) -> None:
    _ensure_embedding_keys()
    cases = _load_cases()
    dataset = _build_dataset(cases)
    model = _build_model()
    client = _build_client(upload)

    if client:
        project = client.create_project_if_not_exists(project_key, "Job & CV QA")
        scan = client.scan(project=project, model=model, dataset=dataset)
        scan.upload()
        print("Uploaded scan to Giskard server.")
    else:
        scan = giskard.scan(model=model, dataset=dataset)
        print("Offline scan completed.")

    # Generate HTML report if requested
    if html_report:
        report_path = Path(__file__).parent / "giskard_scan_report.html"
        _generate_html_report(scan, report_path)

    # Provide a lightweight heuristic check so CI can fail fast without parsing reports.
    severe_issues = [issue for issue in getattr(scan, "issues", []) if getattr(issue, "severity", "").upper() == "HIGH"]
    if severe_issues:
        print("High-severity issues detected by Giskard:")
        for issue in severe_issues:
            print(f" - {issue.name}: {issue.description}")
        raise SystemExit(1)
    print("No high-severity Giskard issues detected.")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Giskard QA scan for the job-matching RAG workflow.")
    parser.add_argument("--upload", action="store_true", help="Upload scan results to a running Giskard server.")
    parser.add_argument(
        "--project-key",
        default="hirewire-ai-job-matching",
        help="Giskard project key to use when --upload is set.",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate an HTML report of the scan results.",
    )
    args = parser.parse_args(argv)

    try:
        run_scan(upload=args.upload, project_key=args.project_key, html_report=args.html)
    except SystemExit as exc:
        raise
    except Exception as exc:  # pragma: no cover - defensive logging for dev use
        print(f"Giskard scan failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

