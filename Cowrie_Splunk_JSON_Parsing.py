# https://readthedocs.org/projects/cowrie/downloads/pdf/latest/

import json
import re

import requests
import operator
from country_codes import alpha_2_to_country


def extract_commands():
    eventid = "cowrie.command.input"
    output_file = "commands.txt"
    json_file = "cowrie.json"
    command_check = []

    with open(f"{output_file}", "w") as output_json:

        with open(f"{json_file}", "r+") as cowrie_json:

            # Iterate and load every line
            for line in cowrie_json.readlines():
                data = json.loads(line)

                try:
                    if eventid == data['eventid']:

                        if data['input'] == 'exit':
                            continue

                        # If it's already in the list, it's a duplicate
                        if data['input'] in command_check:
                            continue

                        # Ouput str
                        output_json.writelines(f"{data['input']}\n")

                        # Ouput JSON
                        # json.dump(data['input'], output_json)
                        # [^ ]*\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/[^ ]*
                        # Add to list to prevent duplicates
                        command_check.append(data['input'])

                except KeyError:
                    continue


def match_regular_expression_from_file():
    reg_ex = r"[^ ]*\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/[^ ]*"
    filename = "commands.txt"
    output_file = "ip_list.txt"
    url_list = []

    # Read the lines and parses data with regex and built-in functions
    with open(f"{filename}", "r+") as file:
        for line in file.readlines():
            # url_list += re.findall(reg_ex, line)
            for match in re.findall(reg_ex, line):
                url_list.append(match.rstrip(";").lstrip("http://"))

    # Removes duplicates
    url_list = list(set(url_list))

    # Writes output to file
    with open(f"{output_file}", "w") as file:
        for url in url_list:
            file.writelines(f"{url}\n")


def map_ip_to_country():
    eventid = "src_ip"
    output_file = "ip_countries.txt"
    json_file = "cowrie.json"
    last_seen_ip = "127.0.0.1"
    ip_duplicate_list = []

    # Include encoding to prevent UnicodeEncodeError
    with open(f"{output_file}", "w", encoding="utf-8") as output_file:

        with open(f"{json_file}", "r+") as input_file:

            for line in input_file.readlines():
                ip = json.loads(line)[eventid]

                # Partly helps to prevent duplicate lookups
                # Also reduces ip_list size
                if ip == last_seen_ip:
                    continue

                # Completely eliminates duplicates
                if ip in ip_duplicate_list:
                    continue

                r = requests.get(f"http://ipinfo.io/{ip}?token=REDACTED")
                response_json = r.json()
                output_file.writelines(
                    f"{response_json['ip']},{response_json['region']},"
                    f"{response_json['country']},{response_json['org']}\n"
                )

                last_seen_ip = ip
                ip_duplicate_list.append(ip)


def top_countries():
    output_file = "top_countries.txt"
    input_file = "ip_countries.txt"
    country_count_dict = {}

    with open(f"{output_file}", "w") as output:

        with open(f"{input_file}", "r+", encoding="utf-8") as ips:

            for line in ips.readlines():
                # Basically a CSV file, split by ,
                line = line.split(",")

                # Checks if the key exists
                if line[2] in country_count_dict:
                    country_count_dict[line[2]] += 1

                # If it doesn't exist, create and set as 1
                else:
                    country_count_dict[line[2]] = 1

            for key in country_count_dict.copy():
                try:
                    country_count_dict[alpha_2_to_country[key]] = country_count_dict[key]
                    del country_count_dict[key]

                except KeyError:
                    continue

            country_count_dict_ordered = sorted(country_count_dict.items(), key=operator.itemgetter(1))

            for key, val in country_count_dict_ordered:

                output.writelines(f"{key}:{val}\n")


def create_list_of_ips():
    output_file = "complete_list_of_ips.txt"
    json_file = "cowrie.json"
    eventid = "src_ip"
    ip_list = []
    with open(f"{output_file}", "w") as output:
        with open(f"{json_file}", "r+") as file:
            for line in file.readlines():
                ip = json.loads(line)[eventid]
                if ip in ip_list:
                    continue

                else:
                    ip_list.append(ip)

        for ip in ip_list:
            output.writelines(f"{ip}\n")


def count_ip_interactions():
    list_of_ips = "complete_list_of_ips.txt"
    json_file = "cowrie.json"
    output_file = "ip_occurance_file.txt"
    eventid = "src_ip"

    with open(f"{output_file}", "w")as output:

        with open(f"{json_file}", "r+") as search_file:

            with open(f"{list_of_ips}", "r+") as list_file:

                for ip_from_list in list_file.readlines():
                    # Returns pointer back to start of the file
                    search_file.seek(0)

                    # Counts the number of occurances
                    counter = 0

                    # Strips the newline character from the end of the string
                    ip_from_list = ip_from_list.rstrip("\n")

                    for json_data in search_file.readlines():

                        current_ip = json.loads(json_data)[eventid]
                        # Compares IPs
                        if current_ip == ip_from_list:
                            counter += 1

                    output.writelines(f"{ip_from_list},{counter}\n")


def count_ip_logins():
    eventid = "cowrie.login.success"
    output_file = "ip_login_counts.txt"
    json_file = "cowrie.json"
    list_of_ips = "complete_list_of_ips.tx"

    with open(f"{output_file}", "w")as output:

        with open(f"{json_file}", "r+") as search_file:

            with open(f"{list_of_ips}", "r+") as list_file:

                for ip_from_list in list_file.readlines():
                    # Returns pointer back to start of the file
                    search_file.seek(0)

                    # Counts the number of occurances
                    counter = 0

                    # Strips the newline character from the end of the string
                    ip_from_list = ip_from_list.rstrip("\n")

                    for json_data in search_file.readlines():
                        # Checks if the eventid is for a login
                        if json.loads(json_data)['eventid'] == eventid:
                            current_ip = json.loads(json_data)['src_ip']

                            # Compares IPs
                            if current_ip == ip_from_list:
                                counter += 1
                        else:
                            continue
                    output.writelines(f"{ip_from_list},{counter}\n")
                    print(f"{ip_from_list},{counter}")


def calculate_mean_login_attempts():
    login_count_file = "ip_login_counts.txt"
    with open(f"{login_count_file}", "r") as count_file:

        number_of_lines = len(count_file.readlines())
        total_logins = 0
        count_file.seek(0)
        for line in count_file.readlines():

            total_logins += int(line.split(",")[1].rstrip("\n"))

        print(f"The mean number of logins for a unique IP is: {round(total_logins/number_of_lines, 2)}")


def repetitive_attackers():
    login_count_file = "ip_login_counts.txt"
    with open(f"{login_count_file}", "r") as count_file:
        total = 0

        for line in count_file.readlines():
            ip, num = line.split(",")

            if int(num) > 100:
                num = num.rstrip('\n')
                print(f"{ip} {num}")
                total += int(num)

        print(total)


repetitive_attackers()
