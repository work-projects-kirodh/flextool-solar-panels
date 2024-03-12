import argparse
import json
import os
import subprocess
import shutil
try: 
    from spinedb_api import import_data, DatabaseMapping
except ModuleNotFoundError:
    exit("Cannot find the required Spine-Toolbox module. Check that the environment is activated and the toolbox is installed")


def update_flextool(skip_git):

    shutil.copy("./.spinetoolbox/project.json", "./.spinetoolbox/project_temp.json")
    if not skip_git:
        completed = subprocess.run(["git", "restore", "."])
        if completed.returncode != 0:
            print("Failed to restore version controlled files.")
            exit(-1)

        completed = subprocess.run(["git", "pull"])
        if completed.returncode != 0:
            print("Failed to get the new version.")
            exit(-1)

    migrate_project("./.spinetoolbox/project_temp.json","./.spinetoolbox/project.json")
    os.remove("./.spinetoolbox/project_temp.json")

    from migrate_database import migrate_database
    from initialize_database import initialize_database

    if not os.path.exists("Input_data.sqlite"):
        initialize_database("Input_data.sqlite")
    if not os.path.exists("input_data_template.sqlite"):
        initialize_database("input_data_template.sqlite")

    db_to_update = []
    db_to_update.append("Init.sqlite")
    db_to_update.append("Input_data.sqlite")
    db_to_update.append("input_data_template.sqlite")
    db_to_update.append("time_settings_only.sqlite")

    # add the database used in the input_data tool
    with open("./.spinetoolbox/project.json") as json_file:
        specifications = json.load(json_file)
    path = specifications["items"]["Input_data"]["url"]["database"]["path"]
    db_to_update.append(path)

    # add the databases in the example folder
    dir_list = os.listdir("./how to example databases")
    for i in dir_list:
        if i.endswith(".sqlite"):
            db_to_update.append("how to example databases/" + i)

    # migrate the databases to new version
    for i in db_to_update:
        migrate_database(i)

    result_template_path = './version/flextool_template_results_master.json'
    #replace the template sqlite
    if os.path.exists('Results_template.sqlite'):
        os.remove('Results_template.sqlite')
    initialize_result_database('Results_template.sqlite', result_template_path)

    if not os.path.exists("Results.sqlite"):
        shutil.copy("Results_template.sqlite", "Results.sqlite")
    #update result parameter definitions    
    db = DatabaseMapping('sqlite:///' + 'Results.sqlite', create = False)
    #get template JSON. This can be the master or old template if conflicting migrations in between
    with open (result_template_path) as json_file:
        template = json.load(json_file)
    #these update the old descriptions, but wont remove them or change names (the new name is created, but old stays)
    (num,log) = import_data(db, object_parameters = template["object_parameters"])
    (num,log) = import_data(db, relationship_parameters = template["relationship_parameters"])
    db.commit_session("Updated relationship_parameters, object parameters to the Results.sqlite")

def initialize_result_database(filename,json_path):

    db = DatabaseMapping('sqlite:///' + filename, create = True)

    with open (json_path) as json_file:
        template = json.load(json_file)

    (num,log) = import_data(db,**template)
    print("Result database initialized")
    db.commit_session("Result database initialized")

def migrate_project(old_path, new_path):
    #purpose of this is to update some of the items that users should not need to modify
    #done simply by copying from the git project.json
    #should be replaced if major changes to project.json
    
    #items that are copied
    items = [
        "Initialize",
        "FlexTool3",
        "Export_to_CSV",
        "Import_results",
        "Plot_results",
        "Plot_settings",
    ]

    with open(old_path) as old_json:
        old_dict = json.load(old_json)
    with open(new_path) as new_json:
        new_dict = json.load(new_json)
    
    for item in items:
        if item in old_dict["items"].keys():
            for param in old_dict["items"][item].keys():
                if param != "x" and param != "y":
                    old_dict["items"][item][param] = new_dict["items"][item][param]

    if ("Open_summary" not in old_dict["items"].keys()) and ("Open_summary" in new_dict["items"].keys()):
        old_dict["items"]["Open_summary"] = new_dict["items"]["Open_summary"]
        old_dict["project"]["connections"].append({"name": "from FlexTool3 to Open_summary", "from": ["FlexTool3","bottom"],"to": ["Open_summary","right"]})
        old_dict["project"]["specifications"]["Tool"].append({"type": "path","relative": True,"path": ".spinetoolbox/specifications/Tool/open_summary.json"})

    
    with open("./.spinetoolbox/project_temp2.json", "w") as outfile: 
        json.dump(old_dict, outfile, indent=4)

    shutil.copy("./.spinetoolbox/project_temp2.json", new_path)
    os.remove("./.spinetoolbox/project_temp2.json")

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--skip-git",
        action="store_true",
        help="skip 'git restore' and 'git pull' steps",
    )
    args = arg_parser.parse_args()
    update_flextool(args.skip_git)
