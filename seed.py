"""
seed.py — Loads realistic seed data into CognoDB.

Run with:  python seed.py
Wipes existing data in the DB first, then creates:
  Companies, Skills, Jobs, Candidates and their relationships.

All queries are parameterised (no string-concatenated Cypher).
"""

from db import db

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

COMPANIES = [
    {"name": "Infosys", "industry": "IT Services", "location": "Bengaluru"},
    {"name": "Amazon", "industry": "E-commerce/Cloud", "location": "Hyderabad"},
    {"name": "Zoho", "industry": "SaaS", "location": "Chennai"},
    {"name": "Capgemini", "industry": "IT Consulting", "location": "Pune"},
    {"name": "Sigma AI", "industry": "AI/ML", "location": "Hyderabad"},
]

SKILLS = [
    "Python", "Flask", "Django", "JavaScript", "React", "SQL",
    "Machine Learning", "Data Analysis", "Pandas", "REST APIs",
    "Git", "Docker", "AWS", "HTML/CSS", "Node.js",
]

# Skill adjacency used to seed RELATED_TO relationships (undirected in effect)
SKILL_RELATIONS = [
    ("Python", "Flask"), ("Python", "Django"), ("Python", "Pandas"),
    ("Python", "Machine Learning"), ("Machine Learning", "Data Analysis"),
    ("Data Analysis", "Pandas"), ("Data Analysis", "SQL"),
    ("JavaScript", "React"), ("JavaScript", "Node.js"),
    ("JavaScript", "HTML/CSS"), ("React", "HTML/CSS"),
    ("Flask", "REST APIs"), ("Django", "REST APIs"), ("Node.js", "REST APIs"),
    ("Docker", "AWS"), ("Git", "Docker"), ("SQL", "Django"),
    ("SQL", "Flask"),
]

JOBS = [
    {
        "title": "Python Full Stack Developer",
        "description": "Build and maintain Flask/Django web apps with a "
                        "React frontend.",
        "location": "Hyderabad",
        "company": "Zoho",
        "skills": ["Python", "Flask", "React", "SQL", "REST APIs"],
    },
    {
        "title": "Data Science Intern",
        "description": "Assist in building ML models for demand forecasting.",
        "location": "Bengaluru",
        "company": "Infosys",
        "skills": ["Python", "Machine Learning", "Pandas", "Data Analysis"],
    },
    {
        "title": "Backend Engineer",
        "description": "Design and scale REST APIs on AWS.",
        "location": "Hyderabad",
        "company": "Amazon",
        "skills": ["Python", "Django", "REST APIs", "AWS", "Docker"],
    },
    {
        "title": "ML Engineer",
        "description": "Productionise machine learning pipelines.",
        "location": "Hyderabad",
        "company": "Sigma AI",
        "skills": ["Python", "Machine Learning", "Docker", "AWS"],
    },
    {
        "title": "Frontend Developer",
        "description": "Build responsive UIs with React.",
        "location": "Pune",
        "company": "Capgemini",
        "skills": ["JavaScript", "React", "HTML/CSS"],
    },
    {
        "title": "Junior Software Engineer",
        "description": "Work across the stack on internal tools.",
        "location": "Chennai",
        "company": "Zoho",
        "skills": ["Python", "SQL", "Git", "REST APIs"],
    },
]

CANDIDATES = [
    {
        "name": "Suji", "email": "suji@example.com", "location": "Hyderabad",
        "skills": ["Python", "Flask", "SQL", "Git", "Pandas"],
    },
    {
        "name": "Ravi", "email": "ravi@example.com", "location": "Bengaluru",
        "skills": ["JavaScript", "React", "HTML/CSS", "Node.js"],
    },
    {
        "name": "Siva", "email": "siva@example.com", "location": "Chennai",
        "skills": ["Python", "Machine Learning", "Data Analysis", "Pandas"],
    },
    {
        "name": "Sankar", "email": "sankar@example.com", "location": "Hyderabad",
        "skills": ["Python", "Django", "SQL", "Git"],
    },
    {
        "name": "Sai", "email": "sai@example.com", "location": "Pune",
        "skills": ["Python", "AWS", "Docker", "Git"],
    },
]

def wipe(db_conn):
    db_conn.run_query("MATCH (n) DETACH DELETE n")


def create_constraints(db_conn):
    db_conn.run_query(
        "CREATE CONSTRAINT skill_name IF NOT EXISTS "
        "FOR (s:Skill) REQUIRE s.name IS UNIQUE"
    )
    db_conn.run_query(
        "CREATE CONSTRAINT company_name IF NOT EXISTS "
        "FOR (c:Company) REQUIRE c.name IS UNIQUE"
    )
    db_conn.run_query(
        "CREATE CONSTRAINT job_id IF NOT EXISTS "
        "FOR (j:Job) REQUIRE j.id IS UNIQUE"
    )
    db_conn.run_query(
        "CREATE CONSTRAINT candidate_email IF NOT EXISTS "
        "FOR (c:Candidate) REQUIRE c.email IS UNIQUE"
    )


def seed_skills(db_conn):
    db_conn.run_query(
        "UNWIND $skills AS name MERGE (s:Skill {name: name})",
        {"skills": SKILLS},
    )
    for a, b in SKILL_RELATIONS:
        db_conn.run_query(
            """
            MATCH (a:Skill {name: $a}), (b:Skill {name: $b})
            MERGE (a)-[:RELATED_TO]->(b)
            MERGE (b)-[:RELATED_TO]->(a)
            """,
            {"a": a, "b": b},
        )


def seed_companies(db_conn):
    for c in COMPANIES:
        db_conn.run_query(
            "MERGE (c:Company {name: $name}) "
            "SET c.industry = $industry, c.location = $location",
            c,
        )


def seed_jobs(db_conn):
    for idx, job in enumerate(JOBS, start=1):
        job_id = f"job-{idx}"
        db_conn.run_query(
            """
            MERGE (j:Job {id: $id})
            SET j.title = $title, j.description = $description,
                j.location = $location
            WITH j
            MATCH (c:Company {name: $company})
            MERGE (j)-[:POSTED_BY]->(c)
            """,
            {
                "id": job_id,
                "title": job["title"],
                "description": job["description"],
                "location": job["location"],
                "company": job["company"],
            },
        )
        db_conn.run_query(
            """
            MATCH (j:Job {id: $id})
            UNWIND $skills AS skill_name
            MATCH (s:Skill {name: skill_name})
            MERGE (j)-[:REQUIRES_SKILL]->(s)
            """,
            {"id": job_id, "skills": job["skills"]},
        )


def seed_candidates(db_conn):
    for cand in CANDIDATES:
        db_conn.run_query(
            "MERGE (c:Candidate {email: $email}) "
            "SET c.name = $name, c.location = $location",
            {"email": cand["email"], "name": cand["name"], "location": cand["location"]},
        )
        db_conn.run_query(
            """
            MATCH (c:Candidate {email: $email})
            UNWIND $skills AS skill_name
            MATCH (s:Skill {name: skill_name})
            MERGE (c)-[:HAS_SKILL]->(s)
            """,
            {"email": cand["email"], "skills": cand["skills"]},
        )


def main():
    print("Connecting to CognoDB...")
    db.connect()
    print("Wiping existing data...")
    wipe(db)
    print("Creating constraints...")
    create_constraints(db)
    print("Seeding skills + relations...")
    seed_skills(db)
    print("Seeding companies...")
    seed_companies(db)
    print("Seeding jobs...")
    seed_jobs(db)
    print("Seeding candidates...")
    seed_candidates(db)
    print("Done. Seed data loaded successfully.")
    db.close()


if __name__ == "__main__":
    main()
