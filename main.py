# aws-names

# LICENSE: MIT License, Copyright (C) 2016 Volt Grid Pty Ltd

import os
import sys
import click
import boto3
import requests

from datetime import datetime
from jinja2 import Environment

import json

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--domain', '-d', required=True, multiple=True, help='domain(s) to generate records for.')
@click.option('--allowed-domain', '-a', multiple=True, help='domains allowed to be defined by instance DomainName tags.')
@click.option('--internal', 'val_type', flag_value='internal', default=True, help='uses the instances private IP address in records. [default]')
@click.option('--external', 'val_type', flag_value='external', help='uses the instances public IP address in records.')
@click.option('--cname', 'val_type', flag_value='cname', help='creates CNAME records instead of A records.')
@click.option('--debug', default=False)
def main(**kwargs):
    """Dynamically generates DNS records from EC2 DescribeInstances."""
    if kwargs['debug']: click.echo(pjson(kwargs))

    r = requests.get('http://169.254.169.254/latest/dynamic/instance-identity/document')
    meta_data = r.json()
    if kwargs['debug']: click.echo(pjson(meta_data))

    ec2 = boto3.client('ec2', region_name=meta_data['region'])
    instances = ec2.describe_instances()
    if kwargs['debug']: click.echo(pjson(instances))

    records = []

    for instance in instances['Reservations']:
        try:
            details = {
                'InstanceId': instance['Instances'][0]['InstanceId'],
                'PrivateIpAddress': instance['Instances'][0]['PrivateIpAddress'],
                'PublicIpAddress': instance['Instances'][0]['PublicIpAddress'],
                'PublicDnsName': instance['Instances'][0]['PublicDnsName'],
                'DomainNames': []
            }
            # Loop over tags, pull out useful tags
            for tag in instance['Instances'][0]['Tags']:
                if tag['Key'] == 'Name' and tag['Value'].endswith(kwargs['domain']):
                    for domain in kwargs['domain']:
                        if tag['Value'].endswith(domain):
                            details[tag['Key']] = dns_clean(tag['Value'][:len(tag['Value'])-len(domain)-1]) # -1 to remove .
                elif tag['Key'] in ['Name', 'Role']:
                    details[tag['Key']] = dns_clean(tag['Value'])
                elif kwargs['allowed_domain'] and tag['Key'].startswith('DomainName') and tag['Value'].endswith(kwargs['allowed_domain']):
                    details['DomainNames'].append(tag['Value'])
            records.append(details)
        except KeyError as e:
            print >> sys.stderr, "Skipping %s due to KeyError on: %s" % (instance['Instances'][0]['InstanceId'], e)

    if kwargs['debug']: click.echo(pjson(records))
    render_unbound(records, kwargs['val_type'], kwargs['domain'])

def render_unbound(records, val_type, domain):
    """Renders for use in unbound DNS server"""

    filters = {"value": lambda x, y: {'internal': x['PrivateIpAddress'], 'external': x['PublicIpAddress'], 'cname': x['PublicDnsName']}[y] }

    template = """
{%- for item in records %}{% for domain in domains %}    local-data: "{{ item.InstanceId }}.{{ domain }}. IN A {{ item | value(val_type) }}"
{% if item.Name %}    local-data: "{{ item.Name }}.{{ domain }}. IN A {{ item | value(val_type) }}"
{% endif %}{% if item.Role and item.Name %}    local-data: "{{ item.Name }}.{{ item.Role }}.{{ domain }}. IN A {{ item | value(val_type) }}"
{% endif %}{% endfor %}{% for extra in item.DomainNames %}    local-data: "{{ extra }}. IN A {{ item | value(val_type) }}"
{% endfor %}{% endfor %}"""

    j2_env = Environment()
    j2_env.filters.update(filters)
    output = j2_env.from_string(template).render(records=records, val_type=val_type, domains=domain)
    click.echo(output)

def dns_clean(name):
    """Clean up name to be DNS ready, only allow [a-zA-Z0-9-] and limit to 63 chars"""
    name_clean = ""
    for i in name:
        if i.isalnum() or i in ["-","."]:
            name_clean += i
        if i.isspace():
            name_clean += "-"
    return name_clean[0:63]

# From: jgbarah https://stackoverflow.com/a/22238613/3863307 (CC BY-SA 3.0)
def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError ("Type not serializable")

def pjson(data):
    return json.dumps(data, sort_keys=True, indent=2, separators=(',', ': '), default=json_serial)


if __name__ == '__main__':
    main()
