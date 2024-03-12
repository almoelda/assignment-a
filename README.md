# assignment-a
Python script which handles unauothrized AWS principals on all SQS queues for a single account.

Required environment variables:
-- DESTINATION_BUCKET: S3 bucket name which will contain the result log file with all SQS queues names.

Required configuration:
-- This script use boto3 SDK for AWS.
-- Please follow https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials to configure the client.

Optional Configuration:
-- LOG_MODE: if set to "ON", the script will not patch or modify any SQS queue policy. otherwise it will.

Flow:
-- Listing all available regions for SQS.
-- Listing all SQS queues for a single regions.
-- Analyzing the access policy for each queue. if an external AWS principal found, the script can patch the policy and remove this principals.
-- Logs all queues which had unauthorized AWS principals to file which is uploaded to S3 bucket (need to be defined by environment variable)
