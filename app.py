"""
app.py — Flask web application for the Job Skills Graph.

Backed by CognoDB (graph database) via the official Neo4j driver.
"""

import os
from flask import Flask, render_template, redirect, url_for, flash

from db import db
import queries

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-key-change-me")


@app.errorhandler(RuntimeError)
def handle_db_error(err):
    return render_template("error.html", message=str(err)), 503


@app.route("/")
def home():
    try:
        candidates = queries.list_candidates(db)
        jobs = queries.list_jobs(db)
    except RuntimeError as err:
        return render_template("error.html", message=str(err)), 503
    return render_template("index.html", candidates=candidates, jobs=jobs)


@app.route("/candidate/<email>")
def candidate_view(email):
    try:
        skills = queries.candidate_skills(db, email)
        direct = queries.direct_matches(db, email)
        multi_hop = queries.multi_hop_recommendations(db, email)
        candidates = queries.list_candidates(db)
    except RuntimeError as err:
        return render_template("error.html", message=str(err)), 503

    current = next((c for c in candidates if c["email"] == email), None)
    if current is None:
        flash("Candidate not found.")
        return redirect(url_for("home"))

    return render_template(
        "candidate.html",
        candidate=current,
        skills=skills,
        direct_matches=direct,
        multi_hop=multi_hop,
    )


@app.route("/job/<job_id>")
def job_view(job_id):
    try:
        job = queries.job_details(db, job_id)
    except RuntimeError as err:
        return render_template("error.html", message=str(err)), 503

    if job is None:
        flash("Job not found.")
        return redirect(url_for("home"))

    return render_template("job.html", job=job, job_id=job_id)


@app.route("/almost-there")
def almost_there():
    """Shows the relational-awkward query: candidates missing exactly
    one skill for a job."""
    try:
        rows = queries.almost_qualified_per_job(db)
    except RuntimeError as err:
        return render_template("error.html", message=str(err)), 503
    return render_template("almost_there.html", rows=rows)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
