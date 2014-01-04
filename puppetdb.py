#!/usr/bin/env python
# vim: ts=4 sw=4 et ft=python

import os
import sys

import re
import json
import urllib2
import ConfigParser

from optparse import OptionParser


PUPPETDB = "puppetdb.ini"


def fetch(url, query):
    resp = urllib2.urlopen(url + urllib2.quote(query))
    return json.load(resp)


def fact(key, value):
    return '''
        ["in", "certname",
          ["extract", "certname",
            ["select-facts",
              ["and",
                ["=", "name", "%s"],
                ["=", "value", "%s"]]]]]''' % (key, value)

def query(filter):
    env = os.environ['ECHO_ENV']

    sub_facts = [("echoenvironment", env)]
    return '''
        ["and",
            ["~", "name", "^echoservice_%s$"],
            ["=", "value", "true"],
        %s]''' % (filter, ",".join([fact(k, v) for (k, v) in sub_facts]))

def inventory(data):
    all = {"all": [host['certname'] for host in data]}

    services = {}
    for host in data:
        service = host['name'][12:] # cut off echoservice_
        if not service in services:
            services[service] = [host['certname']]
        else:
            services[service] += [host['certname']]

    prefixes = {}
    for host in data:
        prefix = re.search('^([a-z]+)\d+.', host['certname']).group(1)
        if not prefix in prefixes:
            prefixes[prefix] = [host['certname']]
        else:
            prefixes[prefix] += [host['certname']]
    for host in data:
        try:
            prefix = re.search('^([a-z]+\d+r)\d+.', host['certname']).group(1)
            if not prefix in prefixes:
                prefixes[prefix] = [host['certname']]
            else:
                prefixes[prefix] += [host['certname']]
        except Exception:
            pass

    inventory = {}
    inventory.update(all)
    inventory.update(services)
    inventory.update(prefixes)

    return inventory


def host_fact(key):
    return '''
        ["=", "name", "%s"]''' % (key)

def host_query(filter):
    sub_facts = ["ec2_ami_id",
                 "ec2_ami_launch_index",
                 "ec2_ami_manifest_path",

                 "ec2_block_device_mapping_ami",
                 "ec2_block_device_mapping_ephemeral0",
                 "ec2_block_device_mapping_ephemeral1",
                 "ec2_block_device_mapping_root",
                 "ec2_block_device_mapping_swap",

                "ec2_hostname",
                "ec2_local_hostname",
                "ec2_local_ipv4",
                "ec2_public_hostname",
                "ec2_public_ipv4",

                "ec2_instance_id",
                "ec2_instance_type",
                "ec2_reservation_id",

                "ec2_profile",
                "ec2_kernel_id",
                "ec2_security_groups",

                "ec2_placement_availability_zone",

                "ec2_userdata"]
    return '''
        ["and",
            ["=", "certname", "%s"],
            ["or",
                %s]]''' % (filter, ",".join([host_fact(k) for k in sub_facts]))

def host_inventory(data):
    inventory = {}
    for host in data:
        inventory[host['name']] = host['value']

    return inventory

def read_config(file):
    config = ConfigParser.SafeConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), file)
    config.read(config_path)

    url = config.get('puppetdb', 'url')

    return url

if __name__ == '__main__':
    usage="%prog [--list] [--host <host>]"

    parser = OptionParser(usage=usage)
    parser.add_option("", "--list", action="store_true", dest="list",
        default=False, help="list all hosts")
    parser.add_option("", "--host", action="store", dest="host",
        default=False, help="get all the variables about a specific hosts")

    (options, args) = parser.parse_args()
    url = read_config(PUPPETDB)

    if options.list:
        filter = ".+"
        data = fetch(url, query(filter))
        inv = inventory(data)
    elif options.host:
        filter = options.host
        data = fetch(url, host_query(filter))
        inv = host_inventory(data)
    else:
        parser.print_help()
        sys.exit(1)

    print json.dumps(inv, sort_keys=True, indent=2)

