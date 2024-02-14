import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from TileScheme.WmtsTile import WmtsTile


class ContinuousDB:
    def __init__(self, db_path):
        p = Path(db_path).parent
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)

        self.con = sqlite3.connect(db_path)
        self.cur = self.con.cursor()
    def close(self):
        self.con.close()
    def create_new_db(self):
        self.cur.execute("CREATE TABLE IF NOT EXISTS continuous(time REAL,id TEXT,x INT,y INT,z INT,path TEXT, full_dress INT)")
        self.con.commit()

    def add_tile(self, **kwargs):
        time = kwargs['time'] if 'time' in kwargs else None
        if time == None:
            logging.error("cannot add tile, time missing")
            return
        if not isinstance(time, datetime):
            logging.error("cannot add tile, wrong time type. datetime expected")
            return
        time_str = time.strftime("%Y-%m-%d %H:%M:%S.%f")

        id = str(kwargs['id']) if 'id' in kwargs else None
        x = int(kwargs['x']) if 'x' in kwargs else None
        y = int(kwargs['y']) if 'y' in kwargs else None
        z = int(kwargs['z']) if 'z' in kwargs else None
        path = kwargs['path'] if 'path' in kwargs else None
        full_dress = kwargs['full_dress'] if 'full_dress' in kwargs else None

        self.cur.execute(f"""
            INSERT INTO continuous VALUES
                (julianday('{time_str}'), '{id}', {x},{y},{z},"{path}",{full_dress})
            """)
        self.con.commit()

    def select_tile(self, x: int, y: int, z: int):
        res = self.cur.execute(f"SELECT * FROM continuous WHERE x={x} and y={y} and z={z}")
        return res.fetchall()

    def select_tile_path(self, x: int, y: int, z: int):
        data = self.select_tile(x, y, z)
        if len(data) == 0:
            return None
        if len(data) < 6:
            return None
        return data[0][5]

    def setDate(self, d: datetime):
        self.default_date = d.strftime("%Y-%m-%d %H:%M:%S.%f")

    def setId(self, id: str):
        self.default_id = id

    def save_tile(self, tile: WmtsTile, path: str, full_dress=1):
        time_str = self.default_date
        id = self.default_id
        x = tile.x
        y = tile.y
        z = tile.z
        full_dress = full_dress

        self.cur.execute(f"""
                INSERT INTO continuous VALUES
                    (julianday('{time_str}'), '{id}', {x},{y},{z},"{path}",{full_dress})
                """)
        self.con.commit()
