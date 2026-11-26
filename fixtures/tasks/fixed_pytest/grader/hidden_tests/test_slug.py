from slug import slugify


def check(text, expected):
    result = slugify(text)
    assert type(result) is str, f"expected str, got {type(result).__name__}"
    assert result == expected


def test_basic():
    check("Hello World", "hello-world")


def test_punctuation_and_spaces():
    check("  Reward  Hacking! ", "reward-hacking")


def test_digits():
    check("RFC 008, Level 2", "rfc-008-level-2")
