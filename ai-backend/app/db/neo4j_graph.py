"""
Neo4j Knowledge Graph for SapioCode Curriculum
Graph: Concept nodes → REQUIRES edges → Problem nodes → Student mastery overlay
"""
import os
from typing import Optional, List, Dict, Any

try:
    from neo4j import AsyncGraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "sapiocode")


class CurriculumGraph:
    """
    Manages the curriculum knowledge graph in Neo4j.

    (:Concept)-[:REQUIRES]->(:Concept)
    (:Concept)-[:HAS_PROBLEM]->(:Problem)
    (:Student)-[:MASTERED {p_mastery}]->(:Concept)
    (:Student)-[:ATTEMPTED {attempts, correct}]->(:Problem)
    """

    def __init__(self):
        self._driver = None
        self._connected = False

    async def connect(self):
        if not NEO4J_AVAILABLE:
            print("[Neo4j] neo4j package not installed, using fallback curriculum")
            return
        try:
            self._driver = AsyncGraphDatabase.driver(
                NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            async with self._driver.session() as session:
                await session.run("RETURN 1")
            self._connected = True
            print(f"[Neo4j] Connected to {NEO4J_URI}")
        except Exception as e:
            print(f"[Neo4j] Connection failed: {e}. Using fallback curriculum.")
            self._connected = False

    async def disconnect(self):
        if self._driver:
            await self._driver.close()
            self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ─── Schema Setup ──────────────────────────────────────
    async def setup_schema(self):
        if not self._connected:
            return
        async with self._driver.session() as session:
            await session.run(
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE"
            )
            await session.run(
                "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Problem) REQUIRE p.id IS UNIQUE"
            )
            await session.run(
                "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Student) REQUIRE s.id IS UNIQUE"
            )
            await session.run(
                "CREATE INDEX IF NOT EXISTS FOR (c:Concept) ON (c.name)"
            )

    # ─── Curriculum CRUD ───────────────────────────────────
    async def add_concept(self, concept_id: str, name: str,
                          description: str = "", difficulty: str = "medium") -> bool:
        if not self._connected:
            return False
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (c:Concept {id: $id})
                SET c.name = $name, c.description = $description,
                    c.difficulty = $difficulty
                """,
                id=concept_id, name=name, description=description,
                difficulty=difficulty
            )
        return True

    async def add_prerequisite(self, concept_id: str, requires_id: str) -> bool:
        if not self._connected:
            return False
        async with self._driver.session() as session:
            await session.run(
                """
                MATCH (c:Concept {id: $cid}), (r:Concept {id: $rid})
                MERGE (c)-[:REQUIRES]->(r)
                """,
                cid=concept_id, rid=requires_id
            )
        return True

    async def add_problem_to_concept(self, problem_id: str, concept_id: str,
                                      title: str, difficulty: str = "medium") -> bool:
        if not self._connected:
            return False
        async with self._driver.session() as session:
            await session.run(
                """
                MATCH (c:Concept {id: $cid})
                MERGE (p:Problem {id: $pid})
                SET p.title = $title, p.difficulty = $difficulty
                MERGE (c)-[:HAS_PROBLEM]->(p)
                """,
                pid=problem_id, cid=concept_id, title=title, difficulty=difficulty
            )
        return True

    # ─── Student Progress ──────────────────────────────────
    async def update_student_mastery(self, student_id: str, concept_id: str,
                                      p_mastery: float) -> bool:
        if not self._connected:
            return False
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (s:Student {id: $sid})
                MERGE (c:Concept {id: $cid})
                MERGE (s)-[m:MASTERED]->(c)
                SET m.p_mastery = $p,
                    m.is_mastered = CASE WHEN $p > 0.8 THEN true ELSE false END,
                    m.last_updated = datetime()
                """,
                sid=student_id, cid=concept_id, p=p_mastery
            )
        return True

    async def record_attempt(self, student_id: str, problem_id: str,
                              is_correct: bool) -> bool:
        if not self._connected:
            return False
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (s:Student {id: $sid})
                MERGE (p:Problem {id: $pid})
                MERGE (s)-[a:ATTEMPTED]->(p)
                SET a.attempts = COALESCE(a.attempts, 0) + 1,
                    a.correct = CASE WHEN $correct
                        THEN COALESCE(a.correct, 0) + 1
                        ELSE COALESCE(a.correct, 0) END,
                    a.last_attempt = datetime()
                """,
                sid=student_id, pid=problem_id, correct=is_correct
            )
        return True

    # ─── Navigation (FR-4) ─────────────────────────────────
    async def get_student_curriculum(self, student_id: str) -> List[Dict[str, Any]]:
        """Full curriculum with student mastery overlay. States: locked | current | completed."""
        if not self._connected:
            return self._get_fallback_curriculum()

        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Concept)
                OPTIONAL MATCH (c)-[:REQUIRES]->(prereq:Concept)
                OPTIONAL MATCH (s:Student {id: $sid})-[m:MASTERED]->(c)
                OPTIONAL MATCH (s)-[pm:MASTERED]->(prereq)
                WITH c,
                     COLLECT(DISTINCT {id: prereq.id, mastered: COALESCE(pm.is_mastered, false)}) AS prereqs,
                     COALESCE(m.p_mastery, 0.0) AS mastery,
                     COALESCE(m.is_mastered, false) AS is_mastered
                RETURN c.id AS id, c.name AS name, c.description AS description,
                       c.difficulty AS difficulty, mastery, is_mastered, prereqs
                ORDER BY c.difficulty, c.name
                """,
                sid=student_id
            )

            nodes = []
            async for record in result:
                prereqs = record["prereqs"]
                all_met = all(
                    p.get("mastered", False) for p in prereqs
                    if p.get("id") is not None
                )
                if record["is_mastered"]:
                    state = "completed"
                elif all_met:
                    state = "current"
                else:
                    state = "locked"

                nodes.append({
                    "id": record["id"],
                    "name": record["name"],
                    "description": record["description"],
                    "difficulty": record["difficulty"],
                    "mastery": record["mastery"],
                    "state": state,
                    "prerequisites": [p["id"] for p in prereqs if p.get("id")]
                })
            return nodes

    async def get_next_recommended(self, student_id: str) -> Optional[Dict[str, Any]]:
        """Next concept in Zone of Proximal Development"""
        curriculum = await self.get_student_curriculum(student_id)
        current = [n for n in curriculum if n["state"] == "current"]
        return min(current, key=lambda n: n["mastery"]) if current else None

    async def get_concept_problems(self, concept_id: str) -> List[Dict[str, Any]]:
        if not self._connected:
            return []
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Concept {id: $cid})-[:HAS_PROBLEM]->(p:Problem)
                RETURN p.id AS id, p.title AS title, p.difficulty AS difficulty
                ORDER BY p.difficulty
                """,
                cid=concept_id
            )
            return [dict(record) async for record in result]

    # ─── Teacher Heatmap ───────────────────────────────────
    async def get_class_mastery_grid(self, student_ids: List[str]) -> Dict[str, Any]:
        if not self._connected:
            return {"students": [], "concepts": [], "grid": []}
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Concept)
                WITH COLLECT(c.id) AS concepts, COLLECT(c.name) AS names
                UNWIND $sids AS sid
                OPTIONAL MATCH (s:Student {id: sid})-[m:MASTERED]->(c:Concept)
                WITH sid, concepts, names,
                     COLLECT({concept: c.id, mastery: m.p_mastery}) AS masteries
                RETURN sid AS student_id, concepts, names, masteries
                """,
                sids=student_ids
            )
            grid = []
            concepts = []
            concept_names = []
            async for record in result:
                concepts = record["concepts"]
                concept_names = record["names"]
                mm = {m["concept"]: m["mastery"] for m in record["masteries"] if m["concept"]}
                grid.append({
                    "student_id": record["student_id"],
                    "masteries": [mm.get(c, 0.0) for c in concepts]
                })
            return {"concepts": concepts, "concept_names": concept_names, "grid": grid}

    # ─── Fallback Curriculum ───────────────────────────────
    def _get_fallback_curriculum(self) -> List[Dict[str, Any]]:
        """Static curriculum when Neo4j is unavailable"""
        return [
            {"id": "variables", "name": "Variables & Types", "difficulty": "easy",
             "mastery": 0.0, "state": "current", "prerequisites": [], "description": "Primitive data types, assignment"},
            {"id": "conditionals", "name": "Conditionals", "difficulty": "easy",
             "mastery": 0.0, "state": "locked", "prerequisites": ["variables"], "description": "If/else, boolean logic"},
            {"id": "loops", "name": "Loops", "difficulty": "easy",
             "mastery": 0.0, "state": "locked", "prerequisites": ["conditionals"], "description": "For, while, iteration"},
            {"id": "functions", "name": "Functions", "difficulty": "medium",
             "mastery": 0.0, "state": "locked", "prerequisites": ["loops"], "description": "Definition, parameters, scope"},
            {"id": "arrays", "name": "Arrays & Lists", "difficulty": "medium",
             "mastery": 0.0, "state": "locked", "prerequisites": ["loops"], "description": "Indexing, slicing, operations"},
            {"id": "strings", "name": "String Manipulation", "difficulty": "medium",
             "mastery": 0.0, "state": "locked", "prerequisites": ["arrays"], "description": "Concatenation, parsing"},
            {"id": "recursion", "name": "Recursion", "difficulty": "hard",
             "mastery": 0.0, "state": "locked", "prerequisites": ["functions"], "description": "Base case, recursive step"},
            {"id": "sorting", "name": "Sorting Algorithms", "difficulty": "hard",
             "mastery": 0.0, "state": "locked", "prerequisites": ["arrays", "recursion"], "description": "Bubble, merge, quick sort"},
            {"id": "linked_lists", "name": "Linked Lists", "difficulty": "hard",
             "mastery": 0.0, "state": "locked", "prerequisites": ["arrays", "recursion"], "description": "Singly/doubly linked"},
            {"id": "trees", "name": "Trees", "difficulty": "hard",
             "mastery": 0.0, "state": "locked", "prerequisites": ["linked_lists", "recursion"], "description": "BST, traversal"},
            {"id": "graphs", "name": "Graphs", "difficulty": "hard",
             "mastery": 0.0, "state": "locked", "prerequisites": ["trees"], "description": "BFS, DFS"},
            {"id": "dynamic_programming", "name": "Dynamic Programming", "difficulty": "hard",
             "mastery": 0.0, "state": "locked", "prerequisites": ["recursion", "arrays"], "description": "Memoization, tabulation"},
        ]


# ─── Seed Data ─────────────────────────────────────────────
async def seed_curriculum(graph: CurriculumGraph):
    """Populate Neo4j with the default CS curriculum"""
    if not graph.is_connected:
        print("[Neo4j] Skipping seed — not connected")
        return

    concepts = [
        ("variables", "Variables & Types", "Primitive data types, assignment, type casting", "easy"),
        ("conditionals", "Conditionals", "If/else, switch, boolean logic", "easy"),
        ("loops", "Loops", "For, while, do-while, iteration patterns", "easy"),
        ("functions", "Functions", "Definition, parameters, return values, scope", "medium"),
        ("arrays", "Arrays & Lists", "Indexing, slicing, list operations", "medium"),
        ("strings", "String Manipulation", "Concatenation, parsing, regex basics", "medium"),
        ("recursion", "Recursion", "Base case, recursive step, call stack", "hard"),
        ("sorting", "Sorting Algorithms", "Bubble, merge, quick sort, complexity", "hard"),
        ("linked_lists", "Linked Lists", "Singly/doubly linked, insertion, deletion", "hard"),
        ("trees", "Trees", "Binary trees, BST, traversal", "hard"),
        ("graphs", "Graphs", "BFS, DFS, adjacency representation", "hard"),
        ("dynamic_programming", "Dynamic Programming", "Memoization, tabulation", "hard"),
    ]

    prerequisites = [
        ("conditionals", "variables"),
        ("loops", "conditionals"),
        ("functions", "loops"),
        ("arrays", "loops"),
        ("strings", "arrays"),
        ("recursion", "functions"),
        ("sorting", "arrays"), ("sorting", "recursion"),
        ("linked_lists", "arrays"), ("linked_lists", "recursion"),
        ("trees", "linked_lists"), ("trees", "recursion"),
        ("graphs", "trees"),
        ("dynamic_programming", "recursion"), ("dynamic_programming", "arrays"),
    ]

    for cid, name, desc, diff in concepts:
        await graph.add_concept(cid, name, desc, diff)
    for concept, prereq in prerequisites:
        await graph.add_prerequisite(concept, prereq)

    print(f"[Neo4j] Seeded {len(concepts)} concepts, {len(prerequisites)} prerequisites")


# ─── Singleton ─────────────────────────────────────────────
_curriculum_graph: Optional[CurriculumGraph] = None


def get_curriculum_graph() -> CurriculumGraph:
    global _curriculum_graph
    if _curriculum_graph is None:
        _curriculum_graph = CurriculumGraph()
    return _curriculum_graph
