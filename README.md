ansible-plugins
===============

## inventory/puppetdb.py

Generates inventory that Ansible can undestand by making API request to PuppetDB.

chmod +x puppetdb.py and either name it /etc/ansible/hosts or use ansible with -i to designate the path to the plugin.

The plugin can be useful when you want to use Ansible and Puppet together, or you are in the process of moving from Puppet to Ansible and you need an intermediate period of using both.

Notice: The puppetdb inventory plugin is not quite generic for the moment. Use more as an example.
