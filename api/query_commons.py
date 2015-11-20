from pymysql.cursors import DictCursor

from api import InvalidUsage
from faf import db


def get_select_expressions(fields, field_expression_dict):
    """
    Returns select expressions for all `fields` in `field_expression_dict`.
    Example usage::

        fields = ['id', 'timestamp']
        field_expression_dict = {
            'id': 'map.uid',
            'timestamp': 'UNIX_TIMESTAMP(t.date)',
            'likes': 'feature.likes'
        }

        get_select_expressions(fields, field_expression_dict)

    Result::

        "map.uid as id, UNIX_TIMESTAMP(t.date) as timestamp"

    :param fields: the list of fields to select from `field_expression_dict`. If `None` or empty, all fields will be
    returned
    :param field_expression_dict: a dictionary mapping field names to select expressions. The expressions must not
    contain "as" clauses since they will be appended using the `field` (see example above)
    :return: a select expressions string (see example above)
    """
    if not fields:
        fields = field_expression_dict.keys()

    field_selects = []
    for field in fields:
        if field in field_expression_dict:
            field_selects.append("{} as {}".format(field_expression_dict[field], field))

    return ', '.join(field_selects)


def get_order_by(sort_expressions, valid_fields):
    """
    Converts the `sort_expression` into an "order by" if all fields are in `field_expression_dict`
    Example usage::

        sort_expression = ['likes', '-timestamp']
        field_expression_dict = {
            'id': 'map.uid',
            'timestamp': 'UNIX_TIMESTAMP(t.date)',
            'likes': 'feature.likes'
        }

        get_order_by(sort_expression, field_expression_dict)

    Result::

        "ORDER BY likes ASC, timestamp DESC"

    :param sort_expressions: a list of json-api conform sort expressions (see example above)
    :param valid_fields: a list of valid sort fields
    :return: an MySQL conform ORDER BY string (see example above) or an empty string if `sort_expression` is None or
    empty
    """
    if not sort_expressions:
        return ''

    order_bys = []

    for expression in sort_expressions:
        if not expression or expression == '-':
            continue

        if expression[0] == '-':
            order = 'DESC'
            column = expression[1:]
        else:
            order = 'ASC'
            column = expression

        if column not in valid_fields:
            raise InvalidUsage("Invalid sort field")

        order_bys.append('{} {}'.format(column, order))

    if not order_bys:
        return ''

    return 'ORDER BY {}'.format(', '.join(order_bys))


def get_limit(page, limit):
    page = int(page)
    limit = int(limit)
    return 'LIMIT {}, {}'.format((page - 1) * limit, limit)


def fetch_data(schema, table, select_expressions, max_page_size, request, where='', args=None, many=True):
    fields = request.values.getlist('fields[{}]'.format(schema.Meta.type_))
    sorts = request.values.getlist('sort')

    # Sanitize fields
    if fields:
        fields = [field for field in fields if field in select_expressions.keys()]
    else:
        fields = select_expressions.keys()

    select_expressions = get_select_expressions(fields, select_expressions)
    order_by_expression = get_order_by(sorts, fields)

    page_size = int(request.values.get('page[size]', max_page_size))
    if page_size > max_page_size:
        raise InvalidUsage("Invalid page size")

    page = int(request.values.get('page[number]', 1))
    if page < 1:
        raise InvalidUsage("Invalid page number")
    limit_expression = get_limit(page, page_size)

    with db.connection:
        cursor = db.connection.cursor(DictCursor)
        cursor.execute("SELECT {} FROM {} {} {} {}"
                       .format(select_expressions, table, order_by_expression, where, limit_expression),
                       args)

        if many:
            result = cursor.fetchall()
        else:
            result = cursor.fetchone()

    if not result:
        return None

    return schema.dump(result, many=many).data
