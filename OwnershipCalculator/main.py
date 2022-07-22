import pandas as pd
from importlib import reload
import OwnershipCalculator.ownership as ow
import glob

import warnings

warnings.simplefilter(action="ignore", category=RuntimeWarning)

PRECISION = 1E-8
reload(ow)
file_names = ["../Data/Example 2 Spreadsheet.xlsx"]  # glob.glob("../Data/*.xlsx")

file_names = glob.glob("../Data/Example 2 Spreadsheet.xlsx")

file_names.sort()
for file_name in file_names:

    print("\nProcessing file {}.".format(file_name))
    input_data = pd.read_excel(file_name, sheetname=None)
    input_data["Entities"]['tax_form'] = input_data["Entities"]['tax_form'].map(
        {"Disregarded": "Corporation", "Corporation": "Corporation", "Partnership": "Partnership",
         "Individual": "Individual"})
    entities = {row.entity_id: ow.Entity(*row) for _, row in input_data['Entities'].iterrows()}
    for _, row in input_data['Relationships'].iterrows():
        owner = entities[row.owner_id]
        sub = entities[row.sub_id]
        relationship = ow.Relationship(row.owner_name, row.owner_id, row.sub_name, row.sub_id, row.relationship, row.value_percentage)
        owner.add_relationship(relationship)
        if relationship.relation_type in ow.INDIVIDUAL_RELATION.keys():
            sub = entities[row.sub_id]
            relation_type = ow.INDIVIDUAL_RELATION[row.relationship]
            relationship = ow.Relationship(row.sub_name, row.sub_id, row.owner_name, row.owner_id, relation_type, row.value_percentage)
            sub.add_relationship(relationship)
        else:
            sub.add_owned_by(relationship)

    ow.get_ownerships(entities)

    for index, row in input_data["318 Outputs"].iterrows():
        demo_percentage = entities[row.owner_id].ownership318[row.sub_id]["value"]
        if abs(demo_percentage - row["318_percentage"]) < PRECISION:
            print("Case {:d} passed".format(index))
        else:
            print("Case {:d} failed:".format(index))
            print("     Demo output: {} has {:.4f} ownership318 in {}".format(
                entities[row.owner_id].legal_name, demo_percentage, entities[row.sub_id].legal_name))
            print("     Correct output: {} has {:.4f} ownership318 in {}".format(
                entities[row.owner_id].legal_name, row["318_percentage"], entities[row.sub_id].legal_name))


    for a in entities.keys():
        ow.print_ownership318(entities[25], entities[a])