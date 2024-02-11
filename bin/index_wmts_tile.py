import os
from datetime import datetime
from reparcellator.ContinuousDB import ContinuousDB

if os.path.exists('c3.db'):
    os.unlink('c3.db')
db = ContinuousDB('c3.db')
db.create_new_db()
db.add_tile(
    **{"time": datetime.now(), "id": "ibwoufho2", "x": 0, "y": 1, "z": 3, "path": "/afad/adfaf/13124.b3dm",
       "full_dress": 1})

db.add_tile(
    **{"time": datetime.now(), "id": "ibwoufho2", "x": 1, "y": 2, "z": 3, "path": "/afad/adfaf/1234.b3dm",
       "full_dress": 1})

db.add_tile(
    **{"time": datetime.now(), "id": "oerugo2", "x": 1, "y": 2, "z": 3, "path": "/bfbd/rrgrdf/1234.b3dm",
       "full_dress": 1})

data = db.select_tile(1, 2, 3)
print(data[0][5])
