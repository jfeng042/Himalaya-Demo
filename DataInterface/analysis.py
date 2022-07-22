import pandas as pd
from importlib import reload
import data_load as ow
import glob
from data_modules import Database

import warnings

warnings.simplefilter(action="ignore", category=RuntimeWarning)

PRECISION = 1E-8
reload(ow)
file_names = glob.glob("../Data/Example 2 Spreadsheet.xlsx")
file_names.sort()

def Sec318(db: Database, host_id, target_id):

    print("\nAnalyzing structure...")

    entities = {}
    for i in db.get_entity_list():
        entities[db.get_id(i)] = ow.Entity(*db.get_info(i))

    cursor = db.cursor.execute("SELECT * FROM relationships").fetchall()
    # print(cursor)
    for _, owner_id, owner_name, sub_id, sub_name, relationship, value_percentage in cursor:
        owner = entities[owner_id]
        sub = entities[sub_id]
        relationship = ow.Relationship(owner_name, owner_id, sub_name, sub_id, relationship, value_percentage)
        owner.add_relationship(relationship)
        sub.add_owned_by(relationship)
        # if relationship.relation_type in ow.INDIVIDUAL_RELATION.keys():
        #     sub = entities[row.sub_id]
        #     relation_type = ow.INDIVIDUAL_RELATION[row.relationship]
        #     relationship = ow.Relationship(row.sub_name, row.sub_id, row.owner_name, row.owner_id, relation_type, row.value_percentage)
        #     sub.add_relationship(relationship)
        # else:

    ow.get_ownerships(entities)
    ow.print_ownership318(entities[host_id], entities[target_id])
