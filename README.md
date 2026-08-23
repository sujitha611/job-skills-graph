# Job Skills Graph

A small web application that helps candidates discover jobs they qualify for
directly — and jobs that open up through *related* skills they don't
technically have yet. Backed by **CognoDB**, a managed graph database, using
the official Neo4j Python driver over Bolt.

---

## 1. Use case

Job matching is usually framed as "does this candidate's skill list overlap
with this job's requirement list?" That's a fine relational query. But real
hiring conversations go further: *"I don't have React, but I know JavaScript
and HTML/CSS — how far off am I really?"*

This app answers that second question by modeling **skills as a graph**,
where related skills (e.g. `Python`↔`Flask`, `JavaScript`↔`React`) are
connected. A candidate isn't just a bag of skills — they sit inside a web of
adjacent, learnable skills, and that web determines which jobs are a
realistic reach versus a random stretch.

### Why a graph database?

In a relational schema, "skills related to skills I have, that are required
by jobs I don't directly qualify for" needs a self-join on a skill-adjacency
table, a join against a candidate-skills table, a join against a
job-requirements table, an anti-join to exclude direct matches, and careful
handling if the adjacency should be searched more than one level deep. Each
extra hop of "relatedness" you want to support means another join, and the
query gets harder to write and slower to reason about as the relationship
gets deeper.

In CognoDB, that same question is a single, readable pattern:

```cypher
(candidate)-[:HAS_SKILL]->(known)-[:RELATED_TO]->(related)<-[:REQUIRES_SKILL]-(job)
```

The relationships are first-class and the traversal depth is just pattern
length — no join tables, no recursive CTEs. That's the core argument for a
graph database here: **the interesting part of this problem is the shape of
the connections, not the rows themselves.**

The same applies to the "almost there" query (candidates missing exactly one
skill for a job) — a set-difference across a variable number of required
skills per job, which is awkward to express generically in SQL but falls out
naturally from graph pattern matching + aggregation (see §5).

---

## 2. Data model

**Nodes:** `Candidate`, `Skill`, `Job`, `Company`

**Relationships:**

```
(Candidate)-[:HAS_SKILL]->(Skill)
(Job)-[:REQUIRES_SKILL]->(Skill)
(Job)-[:POSTED_BY]->(Company)
(Skill)-[:RELATED_TO]->(Skill)      // bidirectional adjacency
```

```
   ┌────────────┐  HAS_SKILL   ┌────────┐  RELATED_TO   ┌────────┐
   │ Candidate  │────────────▶ │ Skill  │──────────────▶│ Skill  │
   └────────────┘              └────────┘                └────────┘
                                     ▲
                                     │ REQUIRES_SKILL
                                     │
                                  ┌──────┐   POSTED_BY   ┌──────────┐
                                  │ Job  │──────────────▶│ Company  │
                                  └──────┘                └──────────┘
```

Properties:
- `Candidate`: `name`, `email` (unique), `location`
- `Skill`: `name` (unique)
- `Job`: `id` (unique), `title`, `description`, `location`
- `Company`: `name` (unique), `industry`, `location`

---

## 3. Project structure

```
jobgraph/
├── app.py              # Flask routes
├── db.py               # CognoDB connection (env-var driven)
├── queries.py          # All Cypher queries, parameterised
├── seed.py             # Loads sample data
├── requirements.txt
├── Procfile            # For Render/Heroku-style deployment
├── .env.example
├── static/css/style.css
└── templates/          # Jinja2 templates
```

---

## 4. Setup and run instructions

### 4.1 Create your CognoDB instance

1. Go to [console.cognodb.com/signup](https://console.cognodb.com/signup) and sign up (no credit card needed).
2. From the console, create a free **c0** instance and pick a region.
3. Copy the connection URI (`bolt+s://<instance-id>.databases.cognodb.cloud`) and the generated password for user `cognodb` — the password is shown only once.

### 4.2 Configure the app

```bash
git clone <this-repo-url>
cd jobgraph
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and fill in COGNODB_URI and COGNODB_PASSWORD
```

Load the environment variables (or use `python-dotenv`, already included):

```bash
export $(cat .env | xargs)      # macOS/Linux
```

### 4.3 Seed the database

```bash
python seed.py
```

This wipes any existing data, creates uniqueness constraints, and loads
sample candidates, skills, jobs, and companies.

### 4.4 Run the app

```bash
python app.py
```

Visit `http://localhost:5000`.

### 4.5 Deploy (e.g. Render)

1. Push this repo to GitHub.
2. Create a new **Web Service** on Render, pointing at the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add `COGNODB_URI`, `COGNODB_USER`, `COGNODB_PASSWORD`, `FLASK_SECRET_KEY` as environment variables in the Render dashboard.

---

## 5. Main queries, explained

All queries live in `queries.py` and are run through the Neo4j driver's
parameter map — no string concatenation anywhere.

**Multi-hop traversal — related-skill recommendations** (`multi_hop_recommendations`):
```cypher
MATCH (c:Candidate {email: $email})-[:HAS_SKILL]->(known:Skill)
      -[:RELATED_TO]->(related:Skill)<-[:REQUIRES_SKILL]-(j:Job)
      -[:POSTED_BY]->(co:Company)
WHERE NOT (c)-[:HAS_SKILL]->(:Skill)<-[:REQUIRES_SKILL]-(j)
...
```
Walks candidate → known skill → related skill → job (3 hops), then excludes
jobs the candidate already directly matches. This is the "opens up through
related skills" section on each candidate's page.

**Relational-awkward query — near misses** (`almost_qualified_per_job`):
```cypher
MATCH (j:Job)-[:REQUIRES_SKILL]->(req:Skill)
WITH j, collect(req) AS required, count(req) AS total_required
MATCH (c:Candidate)
OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill) WHERE s IN required
WITH j, total_required, c, count(s) AS have_count
WHERE total_required - have_count = 1
...
```
For every job, computes how many of its required skills each candidate is
missing, and keeps only the "missing exactly one" rows. In SQL this needs a
per-job-varying skill count handled generically, plus a HAVING clause on a
computed difference — doable, but it stops being a simple join and starts
looking like a small report-generation script.

**Direct matches** (`direct_matches`): straightforward overlap count between
`HAS_SKILL` and `REQUIRES_SKILL`, ranked by match percentage.

---

## 6. Screenshots

*(Add screenshots of the home page, a candidate page, and the "Almost
There" page here after running the app locally.)*

---

## 7. Demo & recording

- Hosted demo: `<add your Render/other free-tier link here>`
- Screen recording: `<add a short screen recording link here>`
