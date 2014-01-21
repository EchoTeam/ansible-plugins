#!/usr/bin/env python
# vim: ts=4 sw=4 et ft=python

import os
import os.path
import sys

import re
import json
import urllib2
import ConfigParser
import time
import pprint

from optparse import OptionParser


PUPPETDB = "puppetdb.ini"
CACHE_PATH = "/tmp/ansible-puppetdb.cache"


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

def unique_list(lst):
    return sorted(list(set(lst)))

def unique_values(d):
    d1 = {}
    for k, v in d.iteritems():
        d1[k] = unique_list(v)
    return d1

def hosts(data):
    return unique_list([item['certname'] for item in data])        

def inventory(data, hosts_data):
    all = {"all": unique_list([host['certname'] for host in data])}

    services = {}
    hostvars = {}

    for host in data:
        service = host['name'][12:] # cut off echoservice_
        hostname = host['certname']
        if not service in services:
            services[service] = [hostname]
        else:
            services[service] += [hostname]

    for host in data:
        hostvars[host['certname']] = hosts_data[host['certname']]
    
    meta = {"_meta": {"hostvars" : hostvars}}

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

    services = unique_values(services)
    prefixes = unique_values(prefixes)

    inventory = {}
    inventory.update(meta)
    inventory.update(all)
    inventory.update(services)
    inventory.update(prefixes)

    return inventory


def host_fact(k, v):
    if v[0] == '~':
        return '''
            ["~", "%s", "%s"]''' % (k, v[1:])
    else: 
        return '''
            ["=", "%s", "%s"]''' % (k, v)

def host_query(hosts):
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

                 "ec2_userdata",
                 "~^echoservice_"]
    return '''
        ["and",
            ["in", "certname",
                ["extract", "certname",
                    ["select-facts",
                        ["and",
                            ["=", "name", "echoenvironment"],
                            ["=", "value", "staging"]]]]],

            ["or", %s]]''' % (",".join([host_fact("name", k) for k in sub_facts]))

def host_inventory(data):
    def sname(service):
        return 'jskit' if service == "echo" else service
    def short_host(host):
        return host.split(".")[0]

    inventory = {}
    for host in data:
        hostname = host['certname']
        name = host['name']
        value = host['value']
        if not inventory.has_key(hostname):
            inventory[hostname] = {"erlnodes" : []}
        found = re.search(r"^echoservice_(.+)$", name)
        if found:
            inventory[hostname]['erlnodes'] += ["%s@%s" % (sname(found.group(1)), short_host(hostname))]
        else:
            inventory[hostname][name] = value

    for hostname in inventory:
        inventory[hostname]['erlnodes'] = unique_list(inventory[hostname]['erlnodes'])

    return inventory

def read_config(file):
    config = ConfigParser.SafeConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), file)
    config.read(config_path)

    host = config.get('puppetdb', 'host')
    port = config.get('puppetdb', 'port')
    expire_cache = config.getint('puppetdb', 'expire_cache')
    
    return {"host": host,
            "port": port,
            "expire_cache": expire_cache}

def fetch_data_cached(config):
    data = {}
    hosts_data = {}

    if os.path.isfile(CACHE_PATH) and (time.time() - os.path.getmtime(CACHE_PATH) < config['expire_cache']):
        f = open(CACHE_PATH, 'r')
        cache_data = json.load(f)
        f.close()
        data = cache_data['data']
        hosts_data = cache_data['hosts_data']
    else:
        filter = ".+"
        data = fetch(url, query(filter))
        hosts_data = fetch(url,host_query(hosts(data)))
        f = open(CACHE_PATH, 'w')
        json.dump({"data": data, "hosts_data": hosts_data}, f, indent=4)
        f.close()
    return (data, hosts_data)

if __name__ == '__main__':
    usage="%prog [--list] [--host <host>]"

    parser = OptionParser(usage=usage)
    parser.add_option("", "--list", action="store_true", dest="list",
        default=False, help="list all hosts")
    parser.add_option("", "--host", action="store", dest="host",
        default=False, help="get all the variables about a specific hosts")

    (options, args) = parser.parse_args()
    config = read_config(PUPPETDB)

    url = "http://%s:%s/v2/facts/?query=" % (config['host'], config['port'])

    (data, hosts_data) = fetch_data_cached(config)

    if options.list:
        hosts_inv = host_inventory(hosts_data)
        inv = inventory(data, hosts_inv)
    elif options.host:
        inv = host_inventory(hosts_data)[options.host]
    else:
        parser.print_help()
        sys.exit(1)

    print json.dumps(inv, sort_keys=True, indent=4)
