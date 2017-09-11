#!/bin/bash -e
#
# Usage: create-empty-volume.sh size-in-GiB availability-zone volume-type
#
# Create an empty EBS volume with an initialized ext4 file system.

cd "$(dirname "$0")"

# Default: 8 GiB
SIZE="${1:-8}"
# Default: us-west-2a
AZ="${2:-us-west-2a}"
# Default: gp2 (general purpose SSD)
TYPE="${3:-gp2}"

echo "Creating volume..."

VOL_ID="$(aws ec2 create-volume \
        --size "${SIZE}" \
        --availability-zone "${AZ}" \
        --volume-type "${TYPE}" \
        --query "VolumeId" | tr -d '"')"

[ -n "${VOL_ID}" ]

echo "Created volume: ${VOL_ID}."

DEVICE=xvdh

echo "Launching instance..."

INSTANCE_ID="$(aws ec2 run-instances \
    --image-id "ami-7105e609" \
    --placement "AvailabilityZone=${AZ}" \
    --user-data "file://mkfs-userdata.sh" \
    --instance-type "t2.micro" \
    --instance-initiated-shutdown-behavior "terminate" \
    --query "Instances[0].InstanceId" | tr -d '"')"

[ -n "${INSTANCE_ID}" ]

echo "Launched instance: ${INSTANCE_ID}."

echo "Waiting for instance to enter running state..."

STATE="unknown"
while [ "${STATE}" != "running" ]; do
    sleep 5
    STATE="$(aws ec2 describe-instances \
        --instance-id "${INSTANCE_ID}" \
        --query "Reservations[0].Instances[0].State.Name" | tr -d '"')"
    echo "${STATE}"
done

echo "Attaching volume..."

aws ec2 attach-volume \
    --volume-id "${VOL_ID}" \
    --instance-id "${INSTANCE_ID}" \
    --device "${DEVICE}"

echo "Waiting for instance to terminate..."

STATE="unknown"
while [ "${STATE}" != "terminated" ]; do
    sleep 5
    STATE="$(aws ec2 describe-instances \
        --instance-id "${INSTANCE_ID}" \
        --query "Reservations[0].Instances[0].State.Name" | tr -d '"')"
    echo "${STATE}"
done

echo "Created filesystem on volume: ${VOL_ID}"
