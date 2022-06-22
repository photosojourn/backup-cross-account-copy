# Backup Cross Account Copy

This Lambda function provides a mechinism to work around the AWS Backup restriction for RDS backups:

> RDS, Aurora, DocumentDB, and Neptune do not support a single copy action that performs both cross-Region AND cross-account backup. You can choose one or the other. You can also use a AWS Lambda script to listen for the completion of your first copy, perform your second copy, then delete the first copy.

[Source](https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html#features-by-resource)

## Environemnt Variables

* IAM_ROLE_ARN - ARN of the role used to run the AWS Backup Copy Job (Required)
* TARGET_VAULT_ARN - ARN of the AWS BAckup Vault you want to copy to (Required)
* ENABLE_XRAY - Enables XRay support (Optional - Defaults to False)

## IAM Permissions for AWS

This lambda function will need the following IAM permissions

* ECR (To Pull Images)
  * ListImages
  * BatchGetImage
* CloudWatch Logs (To create Log Group and write logs)
  * CreateLogGroup
  * PutLogEvents
* Backup (Manage the Backups)
  * DescribeCopyJob
  * DeleteRecoveryPoint
* Xray (optional - Write data to Xray)
  * PutTelemetryRecords
  * PutTraceSegments
