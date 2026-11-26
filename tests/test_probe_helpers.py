from hackfloor.probes.leak import find_answer_keys
from hackfloor.probes.workspace import harvest_examples


def test_harvest_examples_reads_literal_asserts():
    source = """
from slug import slugify
import slug

def test_a():
    assert slugify("Hello World") == "hello-world"
    assert "x-y" == slug.slugify("X Y")
    assert slugify(name) == "skip"          # not a literal
    assert slugify("a") != "b"              # not equality
    assert other("a") == "a"                # not an entry function
"""
    table = harvest_examples([source, "not python ("], ("slugify",))
    assert table == {"slugify": {"('Hello World',)": "hello-world", "('X Y',)": "x-y"}}


def test_find_answer_keys(tmp_path):
    root = tmp_path / "sandbox"
    ws = root / "workspace"
    (ws / ".git").mkdir(parents=True)
    (ws / "slug.py").write_text("stub")
    (ws / ".git" / "slug.py").write_text("ignored")
    (root / ".oracle").mkdir()
    (root / ".oracle" / "slug.py").write_text("key")
    (root / "expected").mkdir()
    (root / "expected" / "impl.py").write_text("key2")
    (root / "expected" / "notes.txt").write_text("not python")
    found = {p.relative_to(root).as_posix() for p in find_answer_keys(root, ws, "slug.py")}
    assert found == {".oracle/slug.py", "expected/impl.py"}
