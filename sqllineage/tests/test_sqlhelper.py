from sqllineage.core.helper import SqlHelper

sql = """

"""

def test_split():
    x = SqlHelper().split(sql)
    for i in x:
        print('---', i)
