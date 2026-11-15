"""Earth's code may read the link and the dial, never the ship's own tables (CLAUDE.md)."""
import ast
import pathlib

EARTH = pathlib.Path(__file__).resolve().parent.parent / "command_center"
SHIP_TABLES = {"Crew", "Reading", "Alert", "Checkin", "Reminder"}


def test_earth_never_imports_the_ships_tables_or_the_ships_code():
    files = sorted(EARTH.glob("*.py"))
    assert files, "command_center/ has no Python files to check"
    for path in files:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = {alias.name for alias in node.names}
                assert not module.startswith("base_station"), f"{path.name} imports {module}"
                assert not (module == "" and "base_station" in names), f"{path.name} imports base_station"
                assert not names & SHIP_TABLES, f"{path.name} imports {sorted(names & SHIP_TABLES)}"
            elif isinstance(node, ast.Import):
                assert not any(alias.name.startswith("base_station") for alias in node.names), \
                    f"{path.name} imports base_station"
