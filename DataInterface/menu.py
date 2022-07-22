from platform import system as sys_name
from subprocess import call as sys_call

from glob import glob
from data_modules import Database
from entity import Entity
from analysis import Sec318
import os
import copy


# def clear_screen():
#     """Clears the terminal screen"""
#     command = "cls" if sys_name().lower() == 'windows' else "clear"
#     sys_call(command)

class Menu:

    def __init__(self, title, options):
        """The menu stores a title and the available options in a dictionary"""
        self.title = title
        self.temp_dict = {}
        for count, item in enumerate(options):
            self.temp_dict[str(count+1)] = item

    def get_command(self) -> str:
        """Displays the Menu with numerical selector for available command, return a str of the command"""
        while True:
            for i in self.temp_dict:
                print("\t[{}] {}".format(i, self.temp_dict[i]))

            a = input("Select: ")
            if a in self.temp_dict:
                command = self.temp_dict[a]
                #clear_screen
                return command
            else:
                print("{} is not a valid command".format(a))
                continue

    def print_title(self, sep="="):
        """Prints title of the menu"""
        print("\n" + " {} ".format(self.title).center(40, sep))


class ProjectMenu(Menu):
    """Sub-menu that manages the project/database that the program uses"""

    def __init__(self):
        super().__init__(title="Projects",
                         options=["New Project",
                                  "Open Project",
                                  "Delete Project",
                                  "Import from Excel",
                                  "Return"])

    def run(self):

        while True:
            self.print_title()
            command = self.get_command()
            if command == "Return":
                break
            elif command == "New Project":
                new_project = input("Enter new project name: ")
                MainMenu(new_project).run()
            elif command == "Open Project":
                print("\nAvailable projects:")
                project_list = [x[12:-7:1] for x in glob("./databases/*.sqlite")]
                opened_project = Menu(" Project", project_list).get_command()
                MainMenu(opened_project).run()
            elif command == "Delete Project":
                print("\nAvailable projects:")
                project_list = [x[12:-7:1] for x in glob("./databases/*.sqlite")]
                del_project = Menu(" Project", project_list).get_command()
                os.remove(os.path.join("./databases", str(del_project) + ".sqlite"))
            else:
                print("Module being developed")


class MainMenu(Menu):
    """Main menu of the program after the relevant project is selected"""

    def __init__(self, db):
        super().__init__(title="Main Menu: {} ".format(db),
                         options=["Manage Entities/Relationships",
                                  "Sec318 Analysis",
                                  "Quit"])
        self.db = Database(db)


    def run(self):
        while True:
            self.db.create_table()
            self.print_title()
            command = self.get_command()
            if command == "Quit":
                self.db.connection.close()
                break
            elif command == "Manage Entities/Relationships":
                ManageEntity(self.db).run()
            elif command == "Sec318 Analysis":
                print("Select the 318 owner:")
                select_host = EntityList(self.db).get_command()
                select_host = self.db.get_id(select_host)
                print("Select the 318 target subsidiary:")
                select_target = EntityList(self.db).get_command()
                select_target = self.db.get_id(select_target)
                Sec318(self.db, select_host, select_target)


class ManageEntity(Menu):

    def __init__(self, db: Database):
        super().__init__(title="Manage Entities",
                         options=["New Entity",
                                  "Manage Existing Entities",
                                  "Return"])
        self.db = db

    def run(self):

        while True:
            self.print_title()
            command = self.get_command()
            if command == "Return":
                break
            elif command == "New Entity":
                info_tuple = entity_info_collect()
                self.db.add_entity(*info_tuple)

            elif command in "Manage Existing Entities":

                print("Entity List".center(40, "-"))

                selection = EntityList(self.db).get_command()

                print("Entity Info: {}".format(selection).center(40, "-"))
                temp_entity = Entity(*self.db.get_info(selection))
                temp_entity.load_relationships(self.db)
                temp_entity.display()
                EntityModules(temp_entity, self.db).run()


class EntityModules(Menu):

    def __init__(self, entity: Entity, db: Database):
        self.db = db
        self.entity = entity
        super().__init__(title="Manage Entity: {}".format(self.entity.entity_name),
                         options=["Update Information",
                                  "Update Owners",
                                  "Update Subsidiaries",
                                  "Delete Entity",
                                  "Return"])

    def run(self):
        while True:
            self.print_title(sep="-")
            command = self.get_command()
            if command == "Return":
                break
            elif command == "Update Information":
                info_tuple = entity_info_collect()
                self.db.add_entity(*info_tuple)

            elif command == "Update Owners":
                if self.entity.tax_classification == "individuals":
                    print("Cannot set owner for individuals")
                    break
                else:
                    while True:
                        options = copy.deepcopy(sorted(self.entity.owners.keys()))
                        options.append("Add New")
                        options.append("Return")
                        owner_menu = Menu("Owners", options)
                        owner_menu.print_title(sep="-")
                        select = owner_menu.get_command()
                        if select == "Return":
                            break
                        if select == "Add New":
                            print("Select New Owner:")
                            select = EntityList(self.db).get_command()
                        percent = percent_input("Ownership percentage:")
                        if percent == 0:
                            self.db.del_relationship(select, self.entity.entity_name)
                        else:
                            self.db.add_relationship(select, self.entity.entity_name, "own", percent)
                        self.entity.load_relationships(self.db)

            elif command == "Update Subsidiaries":
                while True:
                    options = copy.deepcopy(sorted(self.entity.subs.keys()))
                    options.append("Add New")
                    options.append("Return")
                    sub_menu = Menu("Subsidiaries", options)
                    sub_menu.print_title(sep="-")
                    select = sub_menu.get_command()
                    if select == "Return":
                        break
                    if select == "Add New":
                        print("Select New Subsidiary:")
                        select = EntityList(self.db).get_command()
                    percent = percent_input("Ownership percentage:")
                    if percent == 0:
                        self.db.del_relationship(self.entity.entity_name, select)
                    else:
                        self.db.add_relationship(self.entity.entity_name, select, "own", percent)
                    self.entity.load_relationships(self.db)

            elif command == "Delete Entity":
                self.db.del_owners(self.entity.entity_name)
                self.db.del_subs(self.entity.entity_name)
                self.db.del_entity(self.entity.entity_name)
                break


class EntityList(Menu):
    def __init__(self, db: Database):
        super().__init__(title=None, options=db.get_entity_list())


tax_class_Menu = Menu(title="tax classification",
                      options=["corporation",
                               "partnership",
                               "disregarded entity",
                               "individual"])

def entity_info_collect() -> tuple:
    """Collect entity information"""

    while True:
        print("Please provide the following information")
        e_name = str(input("(1) Entity's legal name: "))
        if e_name == "":
            print("legal name cannot be empty")
            continue
        print("(2) Entity's US tax classification:")
        e_form = str(tax_class_Menu.get_command()).lower()
        e_residence = str(input("(3) Entity's tax residence: ")).lower()

        return e_name, e_form, e_residence


def percent_input(prompt) -> float:
    """Validate input is a valid percentage"""

    while True:
        percentage = float(input("{} (0-100): ".format(prompt))) / 100
        if 1 >= percentage >= 0:
            right_percent = percentage
            break
        else:
            print("{} is not a valid percentage".format(percentage * 100))
    return right_percent

if __name__ == "__main__":
    ProjectMenu().run()




