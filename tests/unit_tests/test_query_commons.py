import pytest

from api import InvalidUsage
from api.query_commons import get_select_expressions, get_order_by, get_limit

FIELD_EXPRESSION_DICT = {
    'id': 'map.uid',
    'timestamp': 'UNIX_TIMESTAMP(t.date)',
    'likes': 'feature.likes'
}


def test_get_select_expressions():
    fields = ['id', 'timestamp']

    result = get_select_expressions(fields, FIELD_EXPRESSION_DICT)

    assert result == 'map.uid AS `id`, UNIX_TIMESTAMP(t.date) AS `timestamp`'


def test_get_select_expressions_empty_fields():
    fields = []

    result = get_select_expressions(fields, FIELD_EXPRESSION_DICT)

    assert result.count(',') == 2
    assert 'map.uid AS `id`' in result
    assert 'UNIX_TIMESTAMP(t.date) AS `timestamp`' in result
    assert 'feature.likes AS `likes`' in result


def test_get_select_expressions_none_fields():
    fields = None

    result = get_select_expressions(fields, FIELD_EXPRESSION_DICT)

    assert result.count(',') == 2
    assert 'map.uid AS `id`' in result
    assert 'UNIX_TIMESTAMP(t.date) AS `timestamp`' in result
    assert 'feature.likes AS `likes`' in result


def test_get_order_by():
    sort_expressions = 'likes,-timestamp'

    result = get_order_by(sort_expressions, FIELD_EXPRESSION_DICT)

    assert result.count(',') == 1
    assert 'ORDER BY ' == result[:9]
    assert '`timestamp` DESC' in result
    assert '`likes` ASC' in result


def test_get_order_by_empty():
    result = get_order_by('', FIELD_EXPRESSION_DICT)

    assert result == ''


def test_get_order_by_empty_minus_field():
    result = get_order_by('-', FIELD_EXPRESSION_DICT)

    assert result == ''


def test_get_order_by_partial_empty_fields():
    result = get_order_by('likes,', FIELD_EXPRESSION_DICT)

    assert result == 'ORDER BY `likes` ASC'


def test_get_order_by_empty_fields():
    result = get_order_by(',,', FIELD_EXPRESSION_DICT)

    assert result == ''


def test_get_order_by_none_fields():
    result = get_order_by(None, FIELD_EXPRESSION_DICT)

    assert result == ''


def test_get_order_by_invalid_column():
    with pytest.raises(InvalidUsage) as exception:
        get_order_by('foobar', FIELD_EXPRESSION_DICT)

    assert exception.value.message == 'Invalid sort field'


def test_get_limit():
    assert get_limit(3, 11) == 'LIMIT 22, 11'
