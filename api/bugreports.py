import faf.db as db
from api.query_commons import fetch_data
from faf.api import BugReportSchema
from flask import request

from api import app
from faf.api.bugreport_schema import BugReportStatusSchema

SELECT_EXPRESSIONS = {
    'id': 'bugreports.id',
    'title': 'bugreports.title',
    'target': 'bugreports.target',
    'automatic': 'bugreports.automatic',
    'log': 'bugreports.log',
    'traceback': 'bugreports.traceback',
    'ref': 'bugreport_targets.ref',
    'name': 'bugreport_targets.name',
    'url': 'bugreport_targets.url'
}

TABLE = "bugreports INNER JOIN bugreport_targets on bugreports.target = bugreport_targets.id"
MAX_PAGE_SIZE = 1000

@app.route('/bugs', methods=['GET'])
def list_bugreports():
    def add_bugreport_target(item):
        item['target'] = {
            'name': item['name'],
            'ref': item['ref'],
            'url': item['url']
        }
    return fetch_data(BugReportSchema(), TABLE, SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request, enricher=add_bugreport_target)


@app.route('/bugs', methods=['POST'])
def create_bug():
    schema = BugReportSchema()
    results, errors = schema.loads(request.data.decode('utf-8'))
    if errors:
        return schema.format_errors(errors, many=len(errors) > 1), 400

    report = schema.make_report(**results)

    with db.connection:
        cursor = db.connection.cursor()

        cursor.execute("SELECT id, name, ref from bugreport_targets "
                       "WHERE id = %s", (report.target.id,))

        if not cursor.fetchone():
            cursor.execute("INSERT INTO bugreport_targets (id, name, url, ref) "
                           "VALUES (%s, %s, %s, %s)",
                           (report.target.id, report.target.name, report.target.url, report.target.ref))

        cursor.execute("""INSERT INTO bugreports (title, target, automatic, description, log, traceback)
                          VALUES (%s, %s, %s, %s, %s, %s)""",
                       (report.title, report.target.id, report.automatic, report.description, report.log,
                        report.traceback))
        report.id = cursor.lastrowid

    result, errors = schema.dump(report)
    if errors:
        return schema.format_errors(errors, many=len(errors) > 1), 500

    return result, 201

@app.route('/bugs/<bugreport_id>/status', methods=['POST'])
def add_status(bugreport_id):
    schema = BugReportStatusSchema()
    result, errors = schema.loads(request.data.decode('utf-8'))

    if errors:
        return schema.format_errors(errors, many=len(errors) > 1), 400

    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("SELECT id from bugreports "
                       "WHERE id = %s", (bugreport_id, ))

        row = cursor.fetchone()
        if not row:
            return {}, 404

        cursor.execute("INSERT INTO bugreport_status (bugreport, status_code, url) "
                       "VALUES (%s, %s, %s)", (bugreport_id, result['status_code'], result['url']))
        result['id'] = cursor.lastrowid
        result, _ = schema.dump(result)

        return result, 201
