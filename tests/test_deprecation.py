import pytest
import warnings


def test_frames_py_no_deprecated_utcnow():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from models.frames import ThesisCard

        card = ThesisCard(
            thesis_id="test",
            symbol="RELIANCE",
            direction="LONG",
            setup_type=1,
            trigger=2500,
            invalidation=2450,
            t1=2550,
            t2=2600,
            gross_rr=2.0,
            net_rr=1.8,
            grade="ATTRACTIVE",
            time_decay_multiplier=1.0,
            actionability_tier="Research-Only",
            preferred_regime="Trending-Up",
        )
        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) == 0, (
            f"DeprecationWarnings raised: {deprecation_warnings}"
        )


def test_rest_routes_no_deprecated_utcnow():
    import ast
    import inspect
    from api import rest_routes

    source = inspect.getsource(rest_routes)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "utcnow":
            pytest.fail("rest_routes.py still contains datetime.utcnow()")
