"""
Phase 4 Tests — Teacher Analytics Dashboard

Tests:
  - TeacherAnalytics aggregates data from bkt_local + affect_adapter + integration_bridge
  - Class pulse returns correct shape and values
  - At-risk detection applies correct thresholds
  - Student profile and chat logs are returned correctly
  - Mastery heatmap structure is valid
  - Teacher API endpoints return HTTP 200 with correct JSON structure
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

def _make_bkt_mock(students: dict):
    """
    students = {
        "s1": {"concept_mastery": {"recursion": 0.3, "loops": 0.8}},
        ...
    }
    """
    mock = MagicMock()
    mock._students = {sid: {} for sid in students}

    def get_student_summary(sid):
        return students.get(sid, {"concept_mastery": {}})

    def get_mastery(sid, concept):
        return students.get(sid, {}).get("concept_mastery", {}).get(concept, 0.0)

    def get_weakest_concepts(sid, n=3):
        concepts = students.get(sid, {}).get("concept_mastery", {})
        return sorted(concepts, key=lambda c: concepts[c])[:n]

    mock.get_student_summary.side_effect = get_student_summary
    mock.get_mastery.side_effect = get_mastery
    mock.get_weakest_concepts.side_effect = get_weakest_concepts
    return mock


def _make_affect_mock(profiles: dict):
    """
    profiles = {
        "s1": {"frustration": 0.8, "engagement": 0.2, "confusion": 0.4, "boredom": 0.1},
        ...
    }
    """
    affect_mock = MagicMock()

    class FakeState:
        def __init__(self, d):
            self.frustration = d["frustration"]
            self.engagement  = d["engagement"]
            self.confusion   = d["confusion"]
            self.boredom     = d["boredom"]

    class FakeSmoother:
        def __init__(self, state):
            self._state = state
        def current(self):
            return self._state

    class FakeProfile:
        def __init__(self, d):
            self.smoother = FakeSmoother(FakeState(d))

    affect_mock._profiles = {
        sid: FakeProfile(d) for sid, d in profiles.items()
    }
    return affect_mock


def _make_bridge_mock(hint_history: dict):
    mock = MagicMock()
    mock._hint_history = hint_history
    return mock


# ═══════════════════════════════════════════════════════════════
# Group A — TeacherAnalytics unit tests (isolated)
# ═══════════════════════════════════════════════════════════════

class TestTeacherAnalytics:

    def _build_analytics(self, students=None, affect=None, hints=None):
        from app.services.teacher_analytics import TeacherAnalytics

        students = students or {
            "alice": {"concept_mastery": {"recursion": 0.3, "loops": 0.8}},
            "bob":   {"concept_mastery": {"recursion": 0.7, "loops": 0.6}},
        }
        affect = affect or {
            "alice": {"frustration": 0.75, "engagement": 0.2, "confusion": 0.4, "boredom": 0.0},
            "bob":   {"frustration": 0.1,  "engagement": 0.9, "confusion": 0.1, "boredom": 0.0},
        }
        hints = hints or {
            "alice": [{"text": "hint1"}, {"text": "hint2"}, {"text": "hint3"},
                      {"text": "hint4"}, {"text": "hint5"}, {"text": "hint6"}],
            "bob":   [],
        }

        ta = TeacherAnalytics()
        ta._bkt_engine = _make_bkt_mock(students)
        ta._affect     = _make_affect_mock(affect)
        ta._bridge     = _make_bridge_mock(hints)
        return ta

    # ── Class pulse ───────────────────────────────────────────────

    def test_class_pulse_returns_classPulse(self):
        from app.services.teacher_analytics import ClassPulse
        ta = self._build_analytics()
        pulse = ta.get_class_pulse()
        assert isinstance(pulse, ClassPulse)

    def test_class_pulse_active_students(self):
        ta = self._build_analytics()
        pulse = ta.get_class_pulse()
        assert pulse.active_students == 2

    def test_class_pulse_average_mastery_range(self):
        ta = self._build_analytics()
        pulse = ta.get_class_pulse()
        assert 0.0 <= pulse.average_mastery <= 1.0

    def test_class_pulse_average_frustration(self):
        ta = self._build_analytics()
        pulse = ta.get_class_pulse()
        # alice=0.75, bob=0.1 → avg ≈ 0.425
        assert pytest.approx(pulse.average_frustration, abs=0.01) == 0.425

    def test_class_pulse_at_risk_count(self):
        ta = self._build_analytics()
        pulse = ta.get_class_pulse()
        # alice is at risk (high frustration + many hints + low mastery on recursion)
        assert pulse.at_risk_count >= 1

    def test_class_pulse_no_students(self):
        from app.services.teacher_analytics import TeacherAnalytics
        ta = TeacherAnalytics()
        ta._bkt_engine = _make_bkt_mock({})
        ta._affect     = _make_affect_mock({})
        ta._bridge     = _make_bridge_mock({})
        pulse = ta.get_class_pulse()
        assert pulse.active_students == 0

    def test_class_pulse_most_struggled_concept(self):
        ta = self._build_analytics()
        pulse = ta.get_class_pulse()
        # "recursion" has lowest mastery for alice (0.3)
        assert pulse.most_struggled_concept is not None

    # ── At-risk detection ─────────────────────────────────────────

    def test_at_risk_returns_list(self):
        ta = self._build_analytics()
        result = ta.get_at_risk_students()
        assert isinstance(result, list)

    def test_high_frustration_student_is_at_risk(self):
        ta = self._build_analytics()
        risk_ids = [r.student_id for r in ta.get_at_risk_students()]
        assert "alice" in risk_ids  # frustration=0.75 > 0.65 threshold

    def test_low_risk_student_not_in_at_risk(self):
        ta = self._build_analytics()
        risk = ta.get_at_risk_students()
        bob_risk = next((r for r in risk if r.student_id == "bob"), None)
        # Bob has 0 hints and 0.1 frustration — should be low risk or absent
        if bob_risk:
            assert bob_risk.risk_level == "low"

    def test_at_risk_sorted_high_first(self):
        ta = self._build_analytics()
        risk = ta.get_at_risk_students()
        if len(risk) >= 2:
            level_order = {"high": 0, "medium": 1, "low": 2}
            levels = [level_order[r.risk_level] for r in risk]
            assert levels == sorted(levels)

    def test_at_risk_profile_fields_present(self):
        ta = self._build_analytics()
        risk = ta.get_at_risk_students()
        if risk:
            r = risk[0]
            assert hasattr(r, 'student_id')
            assert hasattr(r, 'risk_level')
            assert hasattr(r, 'risk_reason')
            assert hasattr(r, 'weak_concepts')

    # ── Student profile ───────────────────────────────────────────

    def test_student_profile_contains_bkt(self):
        ta = self._build_analytics()
        profile = ta.get_student_profile("alice")
        assert "bkt_summary" in profile
        assert profile["bkt_summary"]["concept_mastery"]["recursion"] == pytest.approx(0.3)

    def test_student_profile_contains_affect(self):
        ta = self._build_analytics()
        profile = ta.get_student_profile("alice")
        assert "affect_state" in profile
        assert profile["affect_state"]["frustration"] == pytest.approx(0.75)

    def test_student_profile_contains_hints(self):
        ta = self._build_analytics()
        profile = ta.get_student_profile("alice")
        assert profile["total_hints"] == 6

    def test_student_profile_risk_level(self):
        ta = self._build_analytics()
        profile = ta.get_student_profile("alice")
        assert profile["risk_level"] in ("medium", "high")

    # ── Chat logs ─────────────────────────────────────────────────

    def test_chat_logs_returns_list(self):
        ta = self._build_analytics()
        logs = ta.get_chat_logs("alice")
        assert isinstance(logs, list)
        assert len(logs) == 6

    def test_chat_logs_empty_for_no_history(self):
        ta = self._build_analytics()
        logs = ta.get_chat_logs("bob")
        assert logs == []

    # ── Mastery heatmap ───────────────────────────────────────────

    def test_mastery_heatmap_returns_list(self):
        from app.services.teacher_analytics import ConceptMasteryRow
        ta = self._build_analytics()
        rows = ta.get_mastery_heatmap()
        assert isinstance(rows, list)
        assert all(isinstance(r, ConceptMasteryRow) for r in rows)

    def test_mastery_heatmap_has_all_students(self):
        ta = self._build_analytics()
        rows = ta.get_mastery_heatmap()
        row_ids = {r.student_id for r in rows}
        assert "alice" in row_ids
        assert "bob" in row_ids

    def test_mastery_heatmap_concept_values(self):
        ta = self._build_analytics()
        rows = ta.get_mastery_heatmap()
        alice_row = next(r for r in rows if r.student_id == "alice")
        assert alice_row.concept_masteries["recursion"] == pytest.approx(0.3)
        assert alice_row.concept_masteries["loops"] == pytest.approx(0.8)


# ═══════════════════════════════════════════════════════════════
# Group B — Teacher API endpoint tests (HTTP layer)
# ═══════════════════════════════════════════════════════════════

class TestTeacherRoutes:
    """
    Uses FastAPI TestClient with the analytics singleton mocked
    so tests run without any real backend connections.
    """

    @pytest.fixture(autouse=True)
    def setup_mock_analytics(self):
        from app.services.teacher_analytics import TeacherAnalytics, ClassPulse, ConceptMasteryRow, StudentRiskProfile

        ta = TeacherAnalytics()
        students = {
            "alice": {"concept_mastery": {"recursion": 0.3, "loops": 0.8}},
            "bob":   {"concept_mastery": {"recursion": 0.7, "loops": 0.6}},
        }
        affect = {
            "alice": {"frustration": 0.75, "engagement": 0.2, "confusion": 0.4, "boredom": 0.0},
            "bob":   {"frustration": 0.1,  "engagement": 0.9, "confusion": 0.1, "boredom": 0.0},
        }
        hints = {
            "alice": [{"text": "h1"}, {"text": "h2"}, {"text": "h3"},
                      {"text": "h4"}, {"text": "h5"}, {"text": "h6"}],
        }
        ta._bkt_engine = _make_bkt_mock(students)
        ta._affect     = _make_affect_mock(affect)
        ta._bridge     = _make_bridge_mock(hints)

        with patch(
            "app.services.teacher_analytics.get_teacher_analytics",
            return_value=ta,
        ):
            yield

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)

    def test_class_pulse_200(self, client):
        r = client.get("/api/teacher/class-pulse")
        assert r.status_code == 200
        data = r.json()
        assert "active_students" in data
        assert "average_mastery" in data
        assert "at_risk_count" in data

    def test_at_risk_200(self, client):
        r = client.get("/api/teacher/at-risk")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_student_profile_200(self, client):
        r = client.get("/api/teacher/student/alice/profile")
        assert r.status_code == 200
        data = r.json()
        assert data["student_id"] == "alice"
        assert "bkt_summary" in data

    def test_student_profile_404_unknown(self, client):
        r = client.get("/api/teacher/student/nobody/profile")
        assert r.status_code == 404

    def test_chat_logs_200(self, client):
        r = client.get("/api/teacher/student/alice/chat-logs")
        assert r.status_code == 200
        data = r.json()
        assert data["total_hints"] == 6

    def test_mastery_heatmap_200(self, client):
        r = client.get("/api/teacher/mastery-heatmap")
        assert r.status_code == 200
        data = r.json()
        assert "concepts" in data
        assert "students" in data
        assert len(data["students"]) >= 2

    def test_list_students_200(self, client):
        r = client.get("/api/teacher/students")
        assert r.status_code == 200
        data = r.json()
        assert "student_ids" in data
        assert "alice" in data["student_ids"]
