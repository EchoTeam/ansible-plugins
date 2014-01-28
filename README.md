ansible-plugins
===============

## inventory/puppetdb.py

Generates inventory that Ansible can undestand by making API request to PuppetDB.

The plugin can be useful when you want to use Ansible and Puppet together, or you are in the process of moving from Puppet to Ansible and you need an intermediate period of using both.

### How to use

Make script executable:

    $ chmod +x __path__/puppetdb.py

To use it with ansible as inventory script copy it to /etc/ansible/hosts:

    $ cp __path__/puppetdb.py /etc/ansible/hosts

or use with -i to designate the path to the plugin

    $ ansible -i __path__/puppetdb.py ...

or export it as enviroment variable

    $ export ANSIBLE_HOSTS=__path__/puppetdb.py


Notice: The puppetdb inventory plugin is not quite generic for the moment. Use more as an example.
