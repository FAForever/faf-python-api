import json

import pytest

from faf import db
from faf.api import BugReportSchema
from faf.api.bugreport_schema import BugReportStatusSchema
from faf.domain.bugs import BugReport, BugReportTarget

@pytest.fixture()
def reset_database(app):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("TRUNCATE TABLE bugreport_targets")
        cursor.execute("TRUNCATE TABLE bugreports")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

pytestmark = pytest.mark.usefixtures("reset_database")


def test_report():
    return BugReport('Test',
                     automatic=False,
                     target=BugReportTarget(name='FAForever/test',
                                            url='http://git.faforever.com/FAForever/test',
                                            ref='develop'),
                     description='Test report',
                     log='<empty>',
                     traceback='<empty>')


def test_no_reports(test_client, app):
    response = test_client.get('/bugs')
    assert json.loads(response.data.decode()) == {"data": []}


def test_manual_report(test_client, app):
    report = test_report()

    s = BugReportSchema()
    data, errors = s.dumps(report)
    assert not errors

    response = test_client.post('/bugs', data=data)
    assert response.status_code == 201

    s = BugReportSchema(many=True)
    response = test_client.get('/bugs')
    result, errors = s.loads(response.data.decode(), many=True)
    assert not errors


def test_add_status_update(test_client, app):
    report = test_report()

    s = BugReportSchema()
    data, errors = s.dumps(report)
    response = json.loads(test_client.post('/bugs', data=data).data.decode())
    id = response['data']['id']

    status = {'data': {
        'bugreport': id,
        'attributes': {
            'status_code': 'filed',
            'url': 'http://github.com/FAForever/test/issues/1',
        },
        'type': 'bugreport_status'
    }}

    s = BugReportStatusSchema()
    response = test_client.post('/bugs/{}/status'.format(id), data=json.dumps(status))
    assert response.status_code == 201

    result, errors = s.loads(response.data.decode(), many=False)
    assert not errors
