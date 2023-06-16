import pytest
from pytest_lazyfixture import lazy_fixture
from app.utils.general import (  # type: ignore
    is_end_of_sentence, startswith_itemize, endswith_hyphen,
    whitespaces_to_single_space
)


@pytest.fixture
def sentence() -> str:
    return ('Hello, this is a phrase; and it continues. With? Two more! words. \n')


@pytest.mark.parametrize(
    'text, flag', [
        (lazy_fixture('sentence'), True),
        ('Hello, this is a phrase!! \t', True),
        ('phrase with footnote. 1 \n \t', True),
        ('Is this is a phrase too?\n', True),
        (' !?? . . \f \v .\n \v', True),
        ('δωμάτιο αρχίζει να θερμαίνεταις. \n', True),
        ('And this one; \n', False),
        ('Hello, this is a phrase; and, \n', False),
        ('Hello, this is a phrase; and \n', False),
    ]
)
def test_end_of_sentence(text: str, flag: bool):
    assert is_end_of_sentence(text) == flag


@pytest.mark.parametrize(
    'text, flag', [
        ('1. This starts with itemize. \n', True),
        ('. This too starts with itemize. \n', True),
        ('1 This does not start with itemize. \n', False),
        ("... This doesn't start with itemize. \n", False),
        (lazy_fixture('sentence'), False)
    ]
)
def test_startswith_itemize(text: str, flag: bool):
    assert startswith_itemize(text) == flag


@pytest.mark.parametrize(
    'text, flag', [
        ('1. This ends with hyphen - \n', True),
        (lazy_fixture('sentence'), False)
    ]
)
def test_endswith_hyphen(text: str, flag: bool):
    assert endswith_hyphen(text) == flag


@pytest.mark.parametrize(
    'text, expected', [
        ('This \t string is over \n \t \v \n ', 'This string is over '),
    ]
)
def test_whitespaces_to_single_space(text: str, expected: str):
    assert whitespaces_to_single_space(text) == expected
