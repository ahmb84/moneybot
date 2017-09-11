# Deploying moneybot on AWS

This directory contains templates and scripts to get you up and running on AWS with minimal fuss.

## Setup

### Requirements

You will need:
* an AWS account
* AWS credentials (access key and secret)
* the [AWS CLI](http://docs.aws.amazon.com/cli/latest/userguide/installing.html)

### Variables

This guide refers to the following variables:

| Variable | Description | Example |
| -------- | ----------- | ------- |
| `$AZ` | Availability zone in which to run your resources (must belong to the region you are launching in) | `us-west-2a` |
| `$BUCKET` | Name of an S3 bucket you own that will hold the CloudFormation template | `super-duper-moneybot-bucket` |
| `$VOLUME` | ID of an EBS volume that will hold persistent data for moneybot (e.g. Docker and PostgreSQL data) | `vol-0123456789abcdef0` |

For unknown reasons, the `aws` commands below can fail if you try to use traditional environment variables to pass these variables. It is recommended that you actually substitute them into the commands before execution.

### IAM

Normally, an EC2 instance can only be accessed using the key pair specified at time of launch. We use a little magic to make this nicer, but it requires some one-time setup.

Head to the IAM console.

1. Create a group called `ssh` (not necessary to attach any policies or permissions). Create a user you'll use to connect to your instance (or choose an existing one) and add this user to the `ssh` group.
1. Click on the user's "Security credentials" tab and scroll down to "SSH keys for AWS CodeCommit". Upload a key of your choosing – we recommend creating a new one specifically for this purpose.

We're not actually going to use CodeCommit; authenticating SSH users will have their public keys checked against the ones you add here. Any user you add to the `ssh` IAM group can connect using their respective key(s).

### Create a data volume

EC2 instances come and go, but we want our important data to live on. To accomplish this, we store Docker and PostgreSQL's data on a separate volume that will be attached to our EC2 instance at launch time. You only need to do this once.

To create an 8 GiB (should be plenty unless DB needs grow dramatically) volume in your chosen availability zone:
```sh
$ ./aws/scripts/create-empty-volume.sh 8 $AZ
Creating volume...
Created volume: vol-0ac4c9da9cd42c8fd.
Launching instance...
Launched instance: i-045f5c900c52155a7.
Waiting for instance to enter running state...
pending
running
Attaching volume...
{
    "AttachTime": "2017-09-11T01:18:46.395Z",
    "Device": "xvdh",
    "InstanceId": "i-045f5c900c52155a7",
    "State": "attaching",
    "VolumeId": "vol-0ac4c9da9cd42c8fd"
}
Waiting for instance to terminate...
running
running
shutting-down
shutting-down
shutting-down
shutting-down
shutting-down
shutting-down
terminated
Created filesystem on volume: vol-0ac4c9da9cd42c8fd
```

Take note of the volume ID printed by this script; this is your `$VOLUME`.

### Upload CloudFormation template to S3

You'll need to upload your CloudFormation template to S3 before you can use it to create or update a stack. You must do this any time you modify the template, before invoking `aws cloudformation update-stack` (though it shouldn't be necessary for you to modify this template).

```sh
aws s3 cp ./cloudformation/moneybot.yml s3://$BUCKET/cloudformation/
```

## Off to the races

### Managing your stack

When launching your stack for the first time, you'll use `aws cloudformation create-stack`:
```sh
aws cloudformation create-stack \
    --stack-name moneybot \
    --template-url https://s3.amazonaws.com/$BUCKET/cloudformation/moneybot.yml \
    --parameters ParameterKey=AvailabilityZone,ParameterValue=$AZ ParameterKey=VolumeId,ParameterValue=$VOLUME \
    --capabilities CAPABILITY_IAM
```

If you make changes and want to update your existing stack, you'll use `update-stack`:
```sh
aws cloudformation update-stack \
    --stack-name moneybot \
    --template-url https://s3.amazonaws.com/$BUCKET/cloudformation/moneybot.yml \
    --parameters ParameterKey=AvailabilityZone,UsePreviousValue=true ParameterKey=VolumeId,UsePreviousValue=true \
    --capabilities CAPABILITY_IAM
```

You can monitor the status of your stack on the CloudFormation stack. When it changes to `CREATE_COMPLETE` (or `UPDATE_COMPLETE`), it's ready to go.

### Connecting to your instance

Head over to the EC2 console and find your instance (it will have the name `moneybot`). Copy its value for Public DNS (IPv4), e.g. `ec2-XX-XXX-XX-XXX.us-west-2.compute.amazonaws.com`. This is your instance's hostname.

Connect using the name of your chosen IAM user:
```sh
ssh -i ~/.ssh/id_rsa_aws adam@ec2-XX-XXX-XX-XXX.us-west-2.compute.amazonaws.com
```

### Preparing your instance

All the packages you need have already been installed, but there's a small amount of first-time setup to do.

First, start PostgreSQL Docker container:
```sh
sudo docker run -d \
    --env "POSTGRES_PASSWORD=secretpass" \
    --name postgres \
    --publish 5432:5432 \
    --volume /ebs/xvdh/pgdata:/var/lib/postgresql/data \
    postgres:9.6-alpine
```

Clone the moneybot repo:
```sh
git clone git://github.com/elsehow/moneybot.git
```

Create a virtualenv and install dependencies:
```
python3.6 -m venv venv
source venv/bin/activate
pip install wheel
pip install -r requirements.txt
```

### Live trading

Create a `config.yml`, e.g.:
```yaml
postgres:
  host: localhost
  port: 5432
  username: postgres
  password: secretpass
  dbname: postgres

poloniex:
  key: YOUR-API-KEY
  secret: YOUR-API-SECRET

trading:
  fiat: BTC
  interval: 43200  # 12 hours
```

Start a `tmux` (or `screen`) session so trading doesn't stop when you disconnect:
```sh
tmux new -s moneybot
```

You're ready to go! Start trading:
```sh
python3.6 examples/live_trading.py -c config.yml -s buffed-coin -l DEBUG
```

To disconnect from your session (leaving the process running in the background), type `^b d`. To reattach to your session later, run:
```sh
tmux attach -s moneybot
```

If you only have one session running, `tmux attach` will also work.
