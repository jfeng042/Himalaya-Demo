from data_modules import Database


class Entity(object):
    """Primary entity"""

    def __init__(self, entity_id, entity_name, tax_classification, tax_residence=None):
        self.entity_id = entity_id
        self.entity_name = entity_name
        self.tax_classification = tax_classification
        if tax_residence is not None:
            self.tax_residence = tax_residence
        self.subs = dict()
        self.owners = dict()

    def load_relationships(self, db: Database):

        owner_record = db.get_owners(self.entity_name)
        sub_record = db.get_subs(self.entity_name)

        for owner_name, percentage in owner_record:
            self.owners[owner_name] = percentage

        for sub_name, percentage in sub_record:
            self.subs[sub_name] = percentage

    def display(self):
        """Display the information of the entity and its relationships"""

        print("Legal Name: {0.entity_name}\n"
              "Tax Classification: {0.tax_classification}\n"
              "Tax Residence: {0.tax_residence}".format(self))
        print("Owners:")
        for i in self.owners:
            print("\t{0} {1:.0%}".format(i, self.owners[i]))
        print("Subsidiaries:")
        for i in self.subs:
            print("\t{0} {1:.0%}".format(i, self.subs[i]))

    def __str__(self):
        return "Entity({})".format(self.entity_name)
