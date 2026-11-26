from slug import slugify


def test_basic():
    assert slugify("Hello World") == "hello-world"


def test_punctuation_and_spaces():
    assert slugify("  Reward  Hacking! ") == "reward-hacking"
