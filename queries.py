"""
queries.py — All Cypher queries used by the app.

Every query is parameterised via the Neo4j driver's parameter map.
No string concatenation is used to build Cypher.
"""


def list_candidates(db):
    return db.run_query(
        "MATCH (c:Candidate) RETURN c.name AS name, c.email AS email, "
        "c.location AS location ORDER BY c.name"
    )


def list_jobs(db):
    return db.run_query(
        """
        MATCH (j:Job)-[:POSTED_BY]->(co:Company)
        RETURN j.id AS id, j.title AS title, j.location AS location,
               co.name AS company
        ORDER BY j.title
        """
    )


def candidate_skills(db, email):
    return db.run_query(
        """
        MATCH (c:Candidate {email: $email})-[:HAS_SKILL]->(s:Skill)
        RETURN s.name AS skill ORDER BY s.name
        """,
        {"email": email},
    )


def job_details(db, job_id):
    rows = db.run_query(
        """
        MATCH (j:Job {id: $id})-[:POSTED_BY]->(co:Company)
        OPTIONAL MATCH (j)-[:REQUIRES_SKILL]->(s:Skill)
        RETURN j.title AS title, j.description AS description,
               j.location AS location, co.name AS company,
               collect(s.name) AS skills
        """,
        {"id": job_id},
    )
    return rows[0] if rows else None


def direct_matches(db, email):
    """Jobs the candidate directly qualifies for (skill overlap), ranked."""
    return db.run_query(
        """
        MATCH (c:Candidate {email: $email})-[:HAS_SKILL]->(s:Skill)
              <-[:REQUIRES_SKILL]-(j:Job)-[:POSTED_BY]->(co:Company)
        WITH j, co, count(DISTINCT s) AS matched
        MATCH (j)-[:REQUIRES_SKILL]->(all_skills:Skill)
        WITH j, co, matched, count(DISTINCT all_skills) AS total
        RETURN j.id AS id, j.title AS title, co.name AS company,
               matched, total,
               round(100.0 * matched / total) AS match_pct
        ORDER BY match_pct DESC, matched DESC
        """,
        {"email": email},
    )


def multi_hop_recommendations(db, email):
    """
    2+ hop traversal:
    Candidate -> HAS_SKILL -> Skill -> RELATED_TO -> Skill <- REQUIRES_SKILL <- Job
    Finds jobs the candidate doesn't directly qualify for, but whose
    required skills are one hop away from a skill the candidate already has.
    """
    return db.run_query(
        """
        MATCH (c:Candidate {email: $email})-[:HAS_SKILL]->(known:Skill)
              -[:RELATED_TO]->(related:Skill)<-[:REQUIRES_SKILL]-(j:Job)
              -[:POSTED_BY]->(co:Company)
        WHERE NOT (c)-[:HAS_SKILL]->(:Skill)<-[:REQUIRES_SKILL]-(j)
        WITH j, co, collect(DISTINCT related.name) AS via_skills,
             collect(DISTINCT known.name) AS from_skills
        RETURN j.id AS id, j.title AS title, co.name AS company,
               via_skills, from_skills
        ORDER BY j.title
        """,
        {"email": email},
    )


def almost_qualified_per_job(db):
    """
    Query that is awkward in a relational model: for every job, find
    candidates missing exactly one required skill (a variable-overlap
    set-difference pattern best expressed as graph traversal + aggregation).
    """
    return db.run_query(
        """
        MATCH (j:Job)-[:REQUIRES_SKILL]->(req:Skill)
        WITH j, collect(req) AS required, count(req) AS total_required
        MATCH (c:Candidate)
        OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill) WHERE s IN required
        WITH j, total_required, c, count(s) AS have_count
        WHERE total_required - have_count = 1
        MATCH (j)-[:POSTED_BY]->(co:Company)
        RETURN j.title AS job_title, co.name AS company,
               c.name AS candidate, c.email AS email,
               (total_required - have_count) AS missing_count
        ORDER BY j.title, c.name
        """
    )


def missing_skills_for_job(db, email, job_id):
    """Skills the candidate is missing for a specific job."""
    return db.run_query(
        """
        MATCH (j:Job {id: $job_id})-[:REQUIRES_SKILL]->(req:Skill)
        WHERE NOT EXISTS {
            MATCH (c:Candidate {email: $email})-[:HAS_SKILL]->(req)
        }
        RETURN req.name AS missing_skill
        ORDER BY req.name
        """,
        {"email": email, "job_id": job_id},
    )
