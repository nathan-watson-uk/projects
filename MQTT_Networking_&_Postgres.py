import psycopg2
import psycopg2.pool, psycopg2.errors
import paho.mqtt.client as mqtt
import re
import logging
from datetime import datetime

# start hotspot
# sudo systemctl start mosquitto
# sudo systemctl start postgresql


# Number of Maximum Concurrent Connections
max_database_connections = 2
db_table = "sensorData"
broker_ip = "192.168.70.226"

# Change Details For PostgreSQL Database
postgre_pool = psycopg2.pool.SimpleConnectionPool(
    1,
    max_database_connections,
    user="nate",
    password="tempAdminPassword",
    host="localhost",
    database="espDATA"
)


# Function That Checks The Database Table Exist
def init_data_connection():
    try:
        global postgre_pool, db_table

        # Checks That a Pool Has Been Created
        if postgre_pool:
            print("Connection Pool Created")

        # Raises Exception
        else:
            print("It Seems a Pool Doesn't Exist")
            return None

        # Gets a Connection Key From The Pool and Creates a Cursor.
        pg_connection = postgre_pool.getconn()
        c = pg_connection.cursor()

        # Creates Table With Columns
        c.execute(f"""CREATE TABLE {db_table} (id serial primary key, 
        received TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        clients text, temp float, humidity float, co2 float, voc float);
        """)
        print(f"Created Table {db_table}")
        # Commits Changes | Releases The Connection Back To The Pool | Closes the Cursor
        pg_connection.commit()
        c.close()
        postgre_pool.putconn(pg_connection)

    except psycopg2.DatabaseError as err:
        print(f"An Error Occurred {err}")


# Function That Inserts Data Into Database
def insert_sensor_data(cli_id, temp, humidity, co2, voc):
    try:
        global postgre_pool, db_table

        # Raises Exception
        if not postgre_pool:
            print("It Seems a Pool Doesn't Exist")
            return None

        # Gets a Connection Key From The Pool and Creates a Cursor.
        pg_connection = postgre_pool.getconn()
        c = pg_connection.cursor()

        # Creates Table With Columns
        # No Need To Insert Into Automatic Ones (ID & Timestamp)
        try:
            c.execute(f"""INSERT INTO {db_table}(clients, temp, humidity, co2, voc) VALUES (\'""" + cli_id + f"""\', {temp}, {humidity}, {co2}, {voc});""")
        except psycopg2.DatabaseError as err:
            print(f"PostgreSQL Error: {err}")

        # Commits Changes | Releases The Connection Back To The Pool | Closes the Cursor
        pg_connection.commit()
        c.close()
        postgre_pool.putconn(pg_connection)

    except Exception as err:
        print(f"An Error Occurred {err}")


# Sanitize Data to Prevent XSS
def sanitize_insert_data(data_recv):
    data_dict = {}

    # Splits Data Up
    data_recv = data_recv.split(" ")
    data_recv = [val.split(':') for val in data_recv]

    try:
        # Puts Data into Dictionary
        for i in range(0, len(data_recv)):
            data_dict[data_recv[i][0]] = data_recv[i][1]
    except IndexError:
        return None

    # data_dict["ID"]
    for key in data_dict:
        if key =="ID":
            continue

        else:
            # Checks Numerical Sensor Data
            if re.match(r"[0-9]*\.?[0-9]*", data_dict[key]):
                continue
            else:
                print(f"Invalid Data {data_dict[key]}")
                # Log This

    # Checks Device ID Data
    if re.match(r"(?:^|\W)IA(?:$|\W)[0-9]{6}", data_dict["ID"]):
        insert_sensor_data(
            cli_id=data_dict["ID"],
            temp=data_dict["temp"],
            humidity=data_dict["humi"],
            co2=data_dict["CO2"],
            voc=data_dict["tVOC"]
        )
    else:
        print(f"Invalid ID {data_dict['ID']}")
        # Log This


def on_connection(cli, userdata, flags, rc):
    print(f"Connected To Broker | Result Code: {rc}")
    cli.subscribe("foo/bar")


def on_data(cli, userdata, msg):
    # When Data from Subscription is Received
    try:
        sanitize_insert_data(msg.payload.decode())
    except UnicodeDecodeError:
        pass


def on_disconnect(cli, userdata, rc):
    global broker_ip
    if not rc:  # When RC is Zero
        print(f"Client Disconnected Unexpectedly from the Broker ({broker_ip})")
        # Log this


def cli_connect_setup():
    global broker_ip
    cli = mqtt.Client(client_id="IA-000000")  # Creates Client Objects
    cli.username_pw_set("esp_device", "REDACTED")
    try:
        cli.connect(broker_ip, 1883, 60)  # Attempts to Connect to Broker
    except Exception as err:
        print(f"Error Occurred When Trying To Connect To Broker ({broker_ip}) {err}")
        exit()

    cli.on_connect = on_connection
    cli.on_message = on_data
    return cli


def main():
    # Connects to Broker and Begins Loop
    init_data_connection()
    cli_connect_setup().loop_forever()


if __name__ == "__main__":
    main()