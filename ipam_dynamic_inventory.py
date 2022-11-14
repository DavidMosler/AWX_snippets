#!/bin/python3


import os
import sys
import json
import mysql.connector

environments = {"d": "dev", "t": "test", "p": "prod"}
inventory = {}



if sys.argv[1] == "--list":

  # Main countries dictionary
  # example: {'cz': {'children': []}}
  countries_list = ["gl", "cz", "sk", "pl", "it"]
  countries_groups = { key: {"children": []} for key in countries_list }

  # Countries sub groups
  # example: {'cz': {'children': ['cz-dev', 'cz-test', 'cz-prod']}
  for key in countries_groups.keys():
    for suffix in environments.values():
      countries_groups[key]["children"].append(key + "_" + suffix)

  inventory.update(countries_groups)

  main_groups = { key: {"children": []} for key in ["test", "prod"] }

  all_subgroups = {}

  for country in countries_groups.keys():
    for subgroup_list in countries_groups[country].values():
      for subgroup in subgroup_list:
        subgroup_dict = { subgroup :{"hosts": []} }
        all_subgroups.update(subgroup_dict)

        if "prod" in subgroup:
          main_groups["prod"]["children"].append(subgroup)
        else:
          main_groups["test"]["children"].append(subgroup)

  inventory.update(main_groups)



  mydb = mysql.connector.connect(
    host="__MYSQL_HOST__",
    user="__MYSQL_USER__",
    password="__MYSQL_PASSWORD__",
    database="__MYSQL_DATABASE__"
  )

  mycursor = mydb.cursor()
  mycursor.execute("SELECT `hostname` FROM `ipaddresses` WHERE `hostname` LIKE '%11l%' AND `state` = 2 AND `owner` = 'INFRA'")
  servers_list = mycursor.fetchall()

  # Remove duplicite hostnames
  servers = set(servers_list)

  # Add hosts into its country sub groups
  for host in servers:
    # Remove all unwanted characters
    host = str(host)
    host = host.strip("(" + ")" + "," + "'").lower()

    if len(host) != 11:
      raise ValueError("The hostname " + host + " isn't valid: bad lenght!")

    prefix = host[:2]
    if prefix not in countries_list:
      raise ValueError("The hostname " + host + " isn't valid: unknown country!")

    environment = host[-1]
    if environment not in environments:
      raise ValueError("The hostname " + host + " isn't valid: unknown environment!")

    sub_group = prefix + "_" + environments[environment]
    all_subgroups[sub_group]["hosts"].append(host)

  inventory.update(all_subgroups)

  print(json.dumps(inventory))

if sys.argv[1] == "--host":
  print('{"_meta": {"hostvars": {}}}')
