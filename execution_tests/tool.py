import sys
from spinedb_api import DatabaseMapping, from_database

url = sys.argv[1]
db_map = DatabaseMapping(url)
parameter_value = from_database(db_map.query(db_map.parameter_value_sq).first().value)
with open("out.dat", "w") as out_file:
    out_file.write(f"{parameter_value}")
db_map.connection.close()
