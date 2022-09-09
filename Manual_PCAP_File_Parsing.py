class InvalidFileFormat(Exception):
    """
        Before attempting the read the PCAPNG file, the parser checks the file signature (magic numbers) of the file.
        The first 4 octets should be '0A 0D 0D 0A', if these are not present then the parser exits.
    """

    def __init__(self, msg=None):
        if not msg:
            msg = "Invalid File Format the File Signature (Magic Number) does not match."
        super().__init__(msg)


import io
from parser_exceptions import *
from block_types import *
import time
import re


class PacketParser:

    def __init__(self, directory, current_octet=0, block_pos=None, pcap_data=None, pcapng_check=False):
        self.directory = directory
        self.current_octet = current_octet
        self.block_positions = block_pos
        self.pcap_data = pcap_data
        self.pcapng_check = pcapng_check

    def read_pcapng_file_data(self):
        with io.open(self.directory, "rb") as ioPCAP:
            self.pcap_data = ioPCAP.read().hex().upper()
            self.pcap_data = [self.pcap_data[h:h+2] for h in range(0, len(self.pcap_data), 2)]

        PacketParser.check_pcap_data(self)

    def read_pcap_file_data(self):
        with io.open(self.directory, "rb") as ioPCAP:

            raw_hex = ioPCAP.read().hex().upper()   # Why does 16 show the magic numbers?
            readable_data = ""
            hex_conversion_list = [raw_hex[h:h+2] for h in range(0, len(raw_hex), 2)]

            for hexval in hex_conversion_list:
                try:
                    readable_data += bytes.fromhex(hexval).decode('ascii')
                except UnicodeDecodeError:
                    continue

            print(readable_data)

    def read_section_header_block(self):
        if self.pcap_data[0:4] == ["0A", "0D", "0D", "0A"]:
            pass

        else:
            return

        shb_starting_octect = self.current_octet

        # Gets the \n\r\r\n hex signature found at the start of a shb
        shb_signature_hex = self.pcap_data[self.current_octet:self.current_octet + 4]

        # Increases octect position
        self.current_octet += 4

        # Calculates the Octect Position Dynamically
        shb_block_length_hex = self.pcap_data[self.current_octet:self.current_octet+4]

        # Uses Staticmethod to convert Hex List values to an Integer
        shb_block_length = PacketParser.calculate_hex_integer_value(shb_block_length_hex)

        self.current_octet += 4

        shb_magic_number = self.pcap_data[self.current_octet:self.current_octet+4]

        self.current_octet += 4

        # Major Version
        shb_major_version_hex = self.pcap_data[self.current_octet:self.current_octet + 2]
        shb_major_version = PacketParser.calculate_hex_integer_value(shb_major_version_hex)
        self.current_octet += 2

        # Minor Version
        shb_minor_version_hex = self.pcap_data[self.current_octet:self.current_octet + 2]
        shb_minor_version = PacketParser.calculate_hex_integer_value(shb_minor_version_hex)
        self.current_octet += 2

        # Skips Section Length
        self.current_octet += 8

        print(f"""\n\t\t---Section Header Block---
        SHB_Signature: {' '.join(shb_signature_hex)}
        SHB_Block_Length: {shb_block_length} Octets
        SHB_Magic_Number: {' '.join(shb_magic_number)}
        SHB_Version: {shb_major_version}.{shb_minor_version}
        ---Section Header Block End---\n
        """)

        option_details = []

        while True:
            # First two octets is the option hex value
            shb_option = self.pcap_data[self.current_octet:self.current_octet + 2]

            # Uses dictionary to convert hex code to option name
            try:
                shb_option = shb_option_dict[tuple(shb_option)]
            except KeyError:
                # If the next 4 octets are the same as the shb block total length it's the end of the block
                if self.pcap_data[self.current_octet:self.current_octet + 4] == shb_block_length_hex:
                    break

            self.current_octet += 2

            # Gets the option length hex and then converts it to an integer
            shb_option_length_hex = self.pcap_data[self.current_octet:self.current_octet + 2]
            shb_option_length = PacketParser.calculate_hex_integer_value(shb_option_length_hex)
            self.current_octet += 2

            # Adds the 00 padding
            while True:
                if shb_option_length % 8 == 0:
                    break
                else:
                    shb_option_length += 1

            # Uses the option length to pull the right amount of data
            shb_option_content = self.pcap_data[self.current_octet:self.current_octet + shb_option_length]

            option_content = f"\n{shb_option}\n"

            # Iterates through the hex list and attempts to convert to ascii
            for hex_value in shb_option_content:
                try:
                    option_content += bytes.fromhex(hex_value).decode('ascii')
                except UnicodeDecodeError:
                    continue

            # Moves the current octet to the end of the text
            self.current_octet += shb_option_length

            print(option_content)

    def check_pcap_data(self):
        if self.pcap_data[0:4] == ["0A", "0D", "0D", "0A"]:
            self.pcapng_check = True

        else:
            self.pcapng_check = False
            raise InvalidFileFormat()

    @staticmethod
    def calculate_hex_integer_value(hexlist: list):
        return sum([int(h, 16) for h in hexlist])


parser = PacketParser(r"C:\Users\natej\PycharmProjects\pyPP\pcap\bad_traffic2.pcapng")
parser.read_pcapng_file_data()
parser.read_section_header_block()


# Source: https://www.ietf.org/id/draft-tuexen-opsawg-pcapng-03.html#name-general-file-structure

# Credit To:
# Michael Tuexen
# Fulvio Risso
# Jasper Bongertz
# Gerald Combs
# Guy Harris
# Eelco Chaudron
# Michael C. Richardson

block_type_dict = {
    "00000001":	"Interface Description Block (Section 4.2)",
    "00000002": "Packet Block (Appendix A)",
    "00000003": "Simple Packet Block (Section 4.4)",
    "00000004":	"Name Resolution Block (Section 4.5)",
    "00000005":	"Interface Statistics Block (Section 4.6)",
    "00000006": "Enhanced Packet Block (Section 4.3)",
    "00000007": "IRIG Timestamp Block, code also used for Socket Aggregation Event Block",
    "00000008":	"ARINC 429 in AFDX Encapsulation Information Block",
    "00000009":	"systemd Journal Export Block (Section 4.7)",
    "0000000a":	"Decryption Secrets Block (Section 4.8)",
    "00000101":	"Hone Project Machine Info Block (see also Google version)",
    "00000102": "Hone Project Connection Event Block (see also Google version)",
    "00000201":	"Sysdig Machine Info Block",
    "00000202":	"Sysdig Process Info Block, version 1",
    "00000203":	"Sysdig FD List Block",
    "00000204":	"Sysdig Event Block",
    "00000205":	"Sysdig Interface List Block",
    "00000206":	"Sysdig User List Block",
    "00000207":	"Sysdig Process Info Block, version 2",
    "00000208":	"Sysdig Event Block with flags",
    "00000209":	"Sysdig Process Info Block, version 3",
    "00000210":	"Sysdig Process Info Block, version 4",
    "00000211":	"Sysdig Process Info Block, version 5",
    "00000212":	"Sysdig Process Info Block, version 6",
    "00000213":	"Sysdig Process Info Block, version 7",
    "00000BAD":	"Custom Block that rewriters can copy into new files (Section 4.9)",
    "40000BAD":	"Custom Block that rewriters should not copy into new files (Section 4.9)",
    "0A0D0D0A":	"Section Header Block (Section 4.1)"
}


shb_option_dict = {
    ("02", "00"): "shb_hardware",
    ("03", "00"): "shb_os",
    ("04", "00"): "shb_userappl"
}


