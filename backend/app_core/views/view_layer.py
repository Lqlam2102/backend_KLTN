import psycopg2

from app_dynamic.models.schema import DB_NAME
from backend.config import USERNAME_CONNECT_DB, HOSTNAME_CONNECT_DB, PASSWORD_CONNECT_DB, PORT_CONNECT_DB, DB_MAIN
from rest_framework.decorators import api_view
from rest_framework.response import Response


def connect_core(username, password, server, port, db_name):
    try:
        conn = psycopg2.connect(
            database=db_name, user=username, password=password, host=server, port=port
        )
        return conn
    except Exception as ex:
        print(ex)
        return False


@api_view(['GET'])
def get_sqlquery_geo(request, **kwargs):
    model_name = kwargs.get('model_name')
    db_core = connect_core(username=USERNAME_CONNECT_DB, password=PASSWORD_CONNECT_DB,
                           server=HOSTNAME_CONNECT_DB, port=PORT_CONNECT_DB,
                           db_name=DB_MAIN)

    if db_core is False:
        # Cannot connect to DB
        return Response({"massage": "Kết nối csdl thất bại"}, status=404)

    cur = db_core.cursor()
    cur.execute(rf"""SELECT json_agg(ST_AsGeoJSON(t.*)::json)
    FROM tb_dynamic_{model_name} AS t;
    """)

    columns = cur.fetchall()
    cur.close()
    if len(columns):
        # Chuyển đổi danh sách thành chuỗi JSON
        # json_data = json.dumps(columns)

        return Response(columns)

    return Response("no content", status=404)
