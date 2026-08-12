"""
Full API E2E verification (run multiple times).
Covers auth, jobs, resumes, screening, results, candidate portal, interviews, GitHub.
"""
from __future__ import annotations

import io
import sys
import time
import asyncio
from typing import Any, Dict

from fastapi.testclient import TestClient

PASS = 0
FAIL = 0


def ok(cond: bool, msg: str) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")
        raise AssertionError(msg)


def run_once(round_n: int) -> None:
    print(f"\n======== E2E ROUND {round_n} ========")
    from app.main import app
    from app.ai.github_analyzer import extract_github_username, analyze_and_store_github

    client = TestClient(app)
    uniq = int(time.time() * 1000) + round_n
    rec_email = f"rec_{uniq}@e2e.dev"
    cand_email = f"cand_{uniq}@e2e.dev"
    pw = "TestPass123!"

    # Auth
    r = client.post("/auth/signup", json={"email": rec_email, "password": pw, "full_name": "E2E Rec", "role": "recruiter"})
    ok(r.status_code == 200, "recruiter signup")
    rtok = r.json()["access_token"]
    rh = {"Authorization": f"Bearer {rtok}"}

    # Admin signup must be rejected / downgraded
    a = client.post("/auth/signup", json={"email": f"admin_{uniq}@e2e.dev", "password": pw, "full_name": "Hack", "role": "admin"})
    ok(a.status_code == 200 and a.json()["user"]["role"] == "recruiter", "admin role blocked on signup")

    c = client.post("/auth/signup", json={"email": cand_email, "password": pw, "full_name": "E2E Cand", "role": "candidate"})
    ok(c.status_code == 200, "candidate signup")
    ctok = c.json()["access_token"]
    ch = {"Authorization": f"Bearer {ctok}"}

    ok(client.get("/auth/me", headers=rh).status_code == 200, "recruiter /me")
    ok(client.get("/auth/me", headers=ch).status_code == 200, "candidate /me")
    ok(client.get("/health").status_code == 200, "health")

    # Job
    job = client.post("/jobs", headers=rh, json={
        "title": "Backend Engineer",
        "company": "E2E Co",
        "jd_text": "Need Python FastAPI Docker AWS PostgreSQL. 3+ years experience. REST APIs and CI/CD.",
        "required_skills": ["python", "fastapi", "docker", "aws", "postgresql"],
        "min_years_exp": 3,
    })
    ok(job.status_code == 200, "create job")
    job_id = job.json()["id"]

    jobs = client.get("/jobs", headers=rh)
    ok(jobs.status_code == 200 and any(j["id"] == job_id for j in jobs.json()), "list jobs")
    job_row = next(j for j in jobs.json() if j["id"] == job_id)
    ok("result_count" in job_row, "job has result_count field")

    pub = client.get("/jobs/public")
    ok(pub.status_code == 200 and any(j["id"] == job_id for j in pub.json()), "public jobs")

    # Resume upload + screen
    resume_txt = (
        "Alice Chen\nalice@example.com\nSUMMARY\nSenior engineer with 5 years experience.\n"
        "EXPERIENCE\nBuilt FastAPI services on AWS with Docker and PostgreSQL.\n"
        "SKILLS\nPython, FastAPI, Docker, AWS, PostgreSQL, CI/CD, Git\n"
        "PROJECTS\nPlatform API: microservices architecture, reduced latency by 40%.\n"
        "EDUCATION\nB.S. Computer Science\n"
    )
    files = [("files", ("alice.txt", io.BytesIO(resume_txt.encode()), "text/plain"))]
    up = client.post(f"/jobs/{job_id}/resumes", headers=rh, files=files)
    ok(up.status_code == 200 and len(up.json()) == 1, "upload resume")

    screen = client.post(f"/jobs/{job_id}/screen", headers=rh)
    ok(screen.status_code == 200, "screen resumes")

    results = client.get(f"/jobs/{job_id}/results", headers=rh)
    ok(results.status_code == 200 and len(results.json()) >= 1, "get results")
    first = results.json()[0]
    ok(isinstance(first.get("score"), (int, float)), "result has score")
    ok(first.get("candidate_name") is not None, "result enriched without crash")
    # candidate_id for uploaded resume should be empty string, not crash
    ok(first.get("candidate_id", "") == "" or first.get("candidate_id") is None or isinstance(first.get("candidate_id"), str), "candidate_id safe")

    patch = client.patch(f"/results/{first['id']}", headers=rh, json={"status": "shortlisted"})
    ok(patch.status_code == 200 and patch.json()["status"] == "shortlisted", "update result status")

    # Candidate flow
    cup = client.post(
        "/candidate/profile",
        headers=ch,
        files={"file": ("cand.txt", io.BytesIO(resume_txt.encode()), "text/plain")},
    )
    ok(cup.status_code == 200, "candidate upload resume")
    profile = client.get("/candidate/profile", headers=ch)
    ok(profile.status_code == 200 and profile.json().get("has_profile"), "candidate profile")
    profile_id = profile.json()["id"]

    tips = client.get("/candidate/resume-tips", headers=ch)
    ok(tips.status_code == 200 and isinstance(tips.json(), list), "resume tips")

    apply = client.post(f"/candidate/apply/{job_id}", headers=ch)
    ok(apply.status_code == 200, "candidate apply")
    apps = client.get("/candidate/applications", headers=ch)
    ok(apps.status_code == 200 and len(apps.json()) >= 1, "list applications")
    ok("fraud_flags" not in apps.json()[0], "fraud_flags hidden from candidate")

    # Results merge should include application
    results2 = client.get(f"/jobs/{job_id}/results", headers=rh)
    ok(results2.status_code == 200 and len(results2.json()) >= 2, "results merge uploaded + application")

    # Interview
    app_id = apps.json()[0]["id"]
    iv = client.post("/interviews", headers=rh, json={
        "result_id": app_id,
        "scheduled_at": "2030-01-15T10:00:00",
        "duration_minutes": 45,
        "meeting_link": "https://meet.google.com/e2e-test",
        "notes": "E2E interview",
    })
    ok(iv.status_code == 200, "schedule interview")
    my_iv = client.get("/interviews/my-interviews", headers=ch)
    ok(my_iv.status_code == 200 and len(my_iv.json()) >= 1, "candidate sees interview")

    # GitHub analyzer unit + API
    ok(extract_github_username("https://github.com/octocat") == "octocat", "extract username from URL")
    ok(extract_github_username("octocat") == "octocat", "extract bare username")
    ok(extract_github_username("https://github.com/octocat/Hello-World") == "octocat", "extract from repo URL")

    gh_submit = client.post("/candidate/github", headers=ch, json={"github_url": "https://github.com/octocat"})
    ok(gh_submit.status_code == 200, "submit github profile")

    # Run analyzer synchronously to verify persistence (same code path as background)
    loop_result = asyncio.run(analyze_and_store_github(profile_id, "https://github.com/octocat"))
    ok(bool(loop_result and loop_result.get("ok")), f"github analyze_and_store ok ({loop_result})")

    # Allow brief settle then fetch
    for _ in range(10):
        gh = client.get(f"/candidate/github/{profile_id}", headers=ch)
        if gh.status_code == 200 and gh.json().get("has_github"):
            break
        time.sleep(0.5)
    ok(gh.status_code == 200 and gh.json().get("has_github"), "github profile stored and readable")
    ok(gh.json().get("username") == "octocat", "github username matches")
    ok(isinstance(gh.json().get("metrics"), dict), "github metrics present")

    # Invalid github rejected
    bad = client.post("/candidate/github", headers=ch, json={"github_url": "not a url!!!"})
    ok(bad.status_code == 400, "invalid github url rejected")

    # Analytics
    ja = client.get(f"/analytics/jobs/{job_id}", headers=rh)
    ok(ja.status_code == 200 and ja.json().get("total_candidates", 0) >= 1, "job analytics")

    # Semantic search (may be empty if embedding still processing — just ensure endpoint works)
    search = client.post("/search/candidates/semantic", headers=rh, json={"query": "python fastapi backend", "top_k": 5})
    ok(search.status_code == 200 and "results" in search.json(), "semantic search endpoint")

    print(f"======== ROUND {round_n} COMPLETE ========")


def main() -> int:
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    for i in range(1, rounds + 1):
        run_once(i)
    print(f"\nALL DONE — PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
