# AWS Names

Queries AWS EC2 DescribeInstances and generates DNS zone files corresponding to the instances tags and command line options.

AWS Names can generate the following records where the specified domain is `aws.example.com` and Name, Role and DomainName are instance tags.

```
<InstanceId>.aws.example.com
<Name>.aws.example.com
<Name>.<Role>.aws.example.com
<DomainName>
```

## Usage

```
Usage: aws-names.py [OPTIONS]

  Dynamically generates DNS records from EC2 DescribeInstances.

Options:
  -d, --domain TEXT          domain(s) to generate records for.  [required]
  -a, --allowed-domain TEXT  domains allowed to be defined by instance
                             DomainName tags.
  --internal                 uses the instances private IP address in records.
                             [default]
  --external                 uses the instances public IP address in records.
  --cname                    creates CNAME records instead of A records.
  -h, --help                 Show this message and exit.
```

Example

```
python aws-names.py --domain aws.example.com --domain aws.example.internal --allowed-domain example.com
    local-data: "i-12345678.aws.example.com. IN A 172.X.X.XX"
    local-data: "vpn1.aws.example.com. IN A 172.X.X.X"
    local-data: "vpn1.vpn.aws.example.com. IN A 172.X.X.X"
    local-data: "i-12345678.aws.example.internal. IN A 172.X.X.x"
    local-data: "vpn1.aws.example.internal. IN A 172.X.X.X"
    local-data: "vpn1.vpn.aws.example.internal. IN A 172.X.X.X"
    local-data: "vpn.example.com. IN A 172.X.X.X"

```

## AWS IAM Permissions

The only permission needed is `ec2:DescribeInstances`. AWS Names uses boto3 so is capable of using EC2 IAM Roles, Environment variables or the default profile listed in ~/.aws/credentials.

## Extra DomainName

Additional FQDNs can be specified as EC2 instance tags, AWS Names read any tag that starts with `DomainName` for example `DomainName: app1.example.com, DomainName0: app-alias.example.com`.

## Backends

### Unbound

Great when setting up a VPN to securely access your EC2 instances. The unbound backend generates an unbound config format using 'local-data' statements.

## CNAMES

*Not yet implemented*

If you query AWS's DNS servers from within the same VPC AWS will return the instances private IP address. This means that the generated CNAME records can be setup publicly but will still resolve to private/internal addresses when looked up by instances on the same VPC.


## TODO:

* Support CNAME properly
* Support instance numbers when multiple instances exist with the same Name
* Support more backends, dnsmasq, route53, bind/nsd
