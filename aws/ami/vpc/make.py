#!/bin/python

import time
import boto3
ec2 = boto3.client('ec2')

### DUPLICATED GLOBALS
deployzone  ='us-east-1a'
deployzone2  ='us-east-1d'


# makes a vpc

# TODO: check dir
# where=$(pwd)
# where="${where: -3}"
# if test "$where" = "aws"; then
#  echo "running from correct directory"
# else
#  echo "must be run from aws directory with ./ami/vpc/make.sh"
#  exit
# fi

# TODO: include global variables
# . ./master/vars.sh


# GLOBALS
vpc_cidr_block = '10.200.0.0/16'


# make a new vpc with a master 10.0.0.0/16 subnet
response = ec2.create_vpc(
    CidrBlock= vpc_cidr_block,
    InstanceTenancy='default'  # change this - don't rely on default being set to what you think it is
    )
vpc_id = response['Vpc']['VpcId']
print 'vpc_id = ', vpc_id


# enable dns support or modsecurity wont let apache start...
response = ec2.modify_vpc_attribute(
    EnableDnsHostnames={'Value': True }, VpcId=vpc_id)
response = ec2.modify_vpc_attribute(
    EnableDnsSupport={ 'Value': True }, VpcId=vpc_id)

# tag the vpc
response = ec2.create_tags(
    Resources=[ vpc_id ],
    Tags=[
        {
            'Key': 'Name',
            'Value': 'Krypton'
        },
    ]
   )

# wait for the vpc
state = '???'
while (True):
      response = ec2.describe_vpcs(Filters=[], VpcIds=[ vpc_id ])
      state = response['Vpcs'][0]['State']
      print 'State: ', state, '\n'
      if (state != 'pending'):
         break
      time.sleep(3)
    
print "done waiting on vpc"

# create an internet gateway (to allow access out to the internet)
response = ec2.create_internet_gateway()
igw = response['InternetGateway']['InternetGatewayId']
print 'IGW : ', igw

# tag it...
response = ec2.create_tags(
    Resources=[ igw ],
    Tags=[ {'Key': 'Name', 'Value': 'Krypton IGW'}]
    )

# attach the igw to the vpc
print '- attaching igw...'
response = ec2.attach_internet_gateway(
    InternetGatewayId=igw,
    VpcId= vpc_id
    )

print "IGW attached. "


# get the route table id for the vpc (we need it later)
# rtb_id=$(aws ec2 describe-route-tables --filters Name=vpc-id,Values=$vpc_id --output text --query 'RouteTables[*].RouteTableId')
# echo rtb_id=$rtb_id
response = ec2.describe_route_tables(
    Filters=[
        {
            'Name': 'vpc-id',
            'Values': [ vpc_id ],
        },
    ],    
    )
rtb_id = response['RouteTables'][0]['RouteTableId']
print "rtb_id: ", rtb_id

# create our main subnets
# we use 10.200.0.0/24 as our main subnet and 10.200.10.0/24 as a backup for multi-az rds
response = ec2.create_subnet(
    AvailabilityZone = deployzone,
    CidrBlock= '10.200.0.0/24',
    VpcId=vpc_id,
    )
subnet_id = response['Subnet']['SubnetId']
print "subnet_id: ", subnet_id

# tag this subnet
response = ec2.create_tags(
    Resources=[ subnet_id ],
    Tags=[
        {
            'Key': 'subnet',
            'Value': '1'
        },
        {
            'Key': 'Name',
            'Value': 'Krypton sn1'
        },
    ]
   )

# associate this subnet with our route table
response = ec2.associate_route_table(RouteTableId= rtb_id, SubnetId= subnet_id)

# now create  the 10.200.10.0/24 subnet in our secondary deployment zone

response = ec2.create_subnet(
    AvailabilityZone = deployzone2,
    CidrBlock= '10.200.10.0/24',
    VpcId=vpc_id,
    )
subnet_id2 = response['Subnet']['SubnetId']
print "subnet_id2: ", subnet_id2

# tag this subnet
response = ec2.create_tags(
    Resources=[ subnet_id2 ],
    Tags=[
        {
            'Key': 'subnet',
            'Value': '2'
        },
        {
            'Key': 'Name',
            'Value': 'Krypton sn2'
        },
    ]
   )

# associate this subnet with our route table
response = ec2.associate_route_table(RouteTableId= rtb_id, SubnetId= subnet_id2)

# Extra:  tag the route table for easier identification
response = ec2.create_tags(
    Resources=[ rtb_id ],
    Tags=[ {'Key': 'Name', 'Value': 'Krypton route table'}]
    )


# create a route out from our route table to the igw
print 'creating route from igw...'
response = ec2.create_route(
    DestinationCidrBlock='0.0.0.0/0',
    GatewayId= igw,
    RouteTableId= rtb_id,
    )

print "\n\n"
#print "response: \n\n", response, "\n\n\n"

# done
print  '*** VPC setup done!'
