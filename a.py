import boto3
import os
import json

# Boto3 sdk is searching for aws credentials in several locations. 
# We can use one of the ways to configure the SDK as described here: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials

# External Configuraton for this script:
#   Destination Bucket: This script will dump a log file into an S3 bucket, which contains the SQS queues list.
def raiser(ex): raise ex
destination_bucket = os.getenv("DESTINATION_BUCKET") if os.getenv("DESTINATION_BUCKET") != None else raiser(Exception("DESTINATION_BUCKET is not set"))
log_mode = True if os.getenv("LOG_MODE") == "ON" else False
print(f"Running with DESTINATION_BUCKET: {destination_bucket}") 
print(f"Running in LOG_MODE: {log_mode}") 

# Initializing a log.txt file
log_file = open("log.txt", 'w')



# # Get caller identity for account ID
sts = boto3.client('sts')
identity_info = sts.get_caller_identity()
account_id = identity_info['Account']
print(f"Running in Account ID: {account_id}") 


print("Listing all available regions for SQS..")
all_regions = boto3.Session().get_available_regions('sqs')
print(f"Received {len(all_regions)} regions")



def process_sqs_policy(policy):
    external_principal_rule_found = False

    # Cloning a new policy object in case we find unauthorized rules in the AWS Principal block.
    cloned_policy = policy

    array_for_cloned_policy_statement = []

    for statement in policy["Statement"]:
        # Creating a clone for the statement, so we would be able to edit it if needed to reapply the policy
        cloned_statement = statement

        # Checking if AWS parameter in Principal block is an array
        # Looping over the AWS principals and checking for other account ids different than current account id.
        # Any different account ids will be ignored and will not appended to the cloned policy object
        if isinstance(statement['Principal']['AWS'], list):
            aws_principal_object = []
            for principal in statement['Principal']['AWS']:
                if account_id not in principal:
                    external_principal_rule_found = True
                else:
                    aws_principal_object.append(principal)
            cloned_statement['Principal']['AWS'] = aws_principal_object

        # Checking if AWS parameter in Principal block is a string
        # If the the single AWS principal is not the root account id this script runs in, it will override and change it to the account_id captured earlier
        if isinstance(statement['Principal']['AWS'], str):
            aws_principal_object = f"arn:aws:iam::{account_id}:root"
            if account_id not in statement['Principal']['AWS']:
                external_principal_rule_found = True
            cloned_statement['Principal']['AWS'] = aws_principal_object
        # Appending the cloned statement, does not matter if it was fixed by the script or not
        array_for_cloned_policy_statement.append(cloned_statement)
    # Assigning the fixed statements to the cloned policy object
    cloned_policy['Statement'] = array_for_cloned_policy_statement

    # Checking if a single external principal rule has been found in the policy
    # If
    #   Yes: returning the fixed cloned dict
    #   No: returning True boolean
    if external_principal_rule_found:
        return cloned_policy
    else:
        return True

# Function which get a queue and a policy, checks for log_mode variable.
# if log_mode is True: it will not modify the sqs queue policy, otherwise it will.
def override_sqs_access_policy(queue, policy):
    if log_mode:
        print("    Log mode is turned on so no changes are being applied to the queue's access policy")
    else:
        sqs.set_queue_attributes(QueueUrl=queue, Attributes=policy)
        print(f"    Modified policy for queue {queue}")


# We might have disabled regions for some aws accounts. So we can expect InvalidClientTokenId exception for not enabled regions.
# Looping through all regions
for region in all_regions:
    try:
        # Creating SQS client for the region
        sqs = boto3.client('sqs', region_name=region)
        print(f"Listing SQS queues in {region}")

        # List SQS queues in the current region
        response = sqs.list_queues()
        queues = response.get('QueueUrls', [])
        print(f"Received {len(queues)} queues.")
        # Loop over queues in the region
        for queue in queues:
            print(f"    Retrieving policy for {queue}")
            policy = sqs.get_queue_attributes(QueueUrl=queue, AttributeNames=['Policy'])
            print(f"    Processing policy")
            result = process_sqs_policy(json.loads(policy['Attributes']['Policy']))
            if isinstance(result, bool):
                print(f"    No external AWS principals has been detected for {queue}")
            else:
                log_file.write(f"{queue}\n")
                override_sqs_access_policy(queue, {'Policy': json.dumps(result)})
    except Exception as e:
        print(e)
            
# Closing the log file handler
log_file.close()

# Uploading the file
print(f"Uploading log.txt to {destination_bucket}")
s3 = boto3.client('s3')
s3.upload_file("log.txt", destination_bucket, "log.txt")
print("Uploaded")