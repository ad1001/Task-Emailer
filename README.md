# Task-Emailer
Daily task reminder at 6am IST

Uses AWS Infra (Lambda, Api Gateway, Dynamo DB, Event Bridge, Cloudwatch, IAM) for providing rest endpoints for CRUD operation on tasks for specified day, every day a mail is sent to user at 6am IST using event bridge.
