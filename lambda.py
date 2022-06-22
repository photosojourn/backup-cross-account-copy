"""
Lambda function to manage cross account Backups
"""
import os
import boto3
import uuid
from typing import Any, Dict
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools import Logger
from aws_lambda_powertools import Tracer

service_name = "cross-account-backup-mgmt"  # Set service name used by Logger/Tracer here

logger = Logger(service=service_name)
tracer = Tracer(service=service_name, disabled=bool(os.environ["ENABLE_XRAY"]))
aws_region = os.environ["AWS_REGION"]
targetVaultArn = os.environ["TARGET_VAULT_ARN"]
iamRoleArn = os.environ["IAM_ROLE_ARN"]

backup = boto3.client('backup')


def validate_arn(arn: str) -> bool:
    """
    Validates if the arn is an RDS arn

    Parameters
    ----------
    arn: The ARN to validate
    """
    if arn.split(":")[2] == "rds":
        return(True)
    else:
        return(False)


def copy_recovery_point(recoveryPointArn: str, sourceVaultArn: str, destinationVaultArn: str) -> str:
    """
    Copy backup to a new Vault

    Parameters
    ----------
    recoveryPointArn: ARN of the Reocvery Point that you want to copy
    sourceVaultArn: ARN of the source Backup Vault
    destinationVaultArn: ARn of the destination Backup Vault
    """
    try:
        response = backup.start_copy_job(
            RecoveryPointArn=recoveryPointArn,
            SourceBackupVaultName=sourceVaultArn,
            DestinationBackupVaultArn=destinationVaultArn,
            IamRoleArn=iamRoleArn,
            IdempotencyToken=str(uuid.uuid4),
            Lifecycle={
                'MoveToColdStorageAfterDays': 0,
                'DeleteAfterDays': 0
            }
        )
        return(response['CopyJobId'])
    except Exception as e:
        logger.error(e.message)
        return()


def delete_recovery_point(copyJobID: str):
    """
    Delete a Recovery Point once it's been copied

    Parameters
    ----------
    copyJobID: ID of the Copy Job which you want to tidy up after
    """
    try:
        copyJob = backup.describe_copy_job(
            copyJobID=copyJobID
        )

        try:
            logger.info("Deleting duplicate backup: " + copyJob['SourceRecoveryPointArn'])
            backup.delete_recovery_point(
                BackupVaultName=copyJob['SourceBackupVaultArn'],
                RecoveryPointArn=copyJob['SourceRecoveryPointArn']
            )
        except Exception as e:
            logger.error(e.message)
            return()
    except Exception as e:
        logger.error(e.message)
        return()


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Main Lambda entry point.

    Parameters
    ----------
    event: Lambda event object
    context: Lambda context object
    """

    if event["detail-type"] == "Backup Job State Change" and event["detail"]["state"] == "COMPLETED":
        if validate_arn(event['detail']['resourceArn']):
            logger.info("Starting cross account copy for Recovery point" + event["id"])
            copyJobId = copy_recovery_point(
                recoveryPointArn=event['resources'][0],
                sourceVaultArn=event['detail']['backupVaultArn'],
                destinationVaultArn=targetVaultArn
            )
        if copyJobId:
            logger.info("Copy Job started: " + copyJobId)
    elif event["detail-type"] == "Copy Job State Change" and event["detail"]["state"] == "COMPLETED":
        logger.info("House keeping after Copy Job: " + event['detail']['copyJobId'])
        delete_recovery_point(
            copyJobID=event['detail']['copyJobId']
        )

    return {"statusCode": 200}
